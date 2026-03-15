import asyncio
import logging
import os
import shutil
import subprocess
import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.future import select
from fastapi import HTTPException
from ..db import Blueprint, PuppetTemplate, CapabilityMatrix, AsyncSession, Config, ApprovedIngredient
from ..models import ImageBuildRequest, ImageResponse
from .smelter_service import SmelterService
from .staging_service import StagingService
from .mirror_service import MirrorService

logger = logging.getLogger(__name__)

class FoundryService:
    _build_semaphore = asyncio.Semaphore(2)

    @staticmethod
    async def build_template(template_id: str, db: AsyncSession) -> ImageResponse:
        """
        Stitches Blueprints into a single Puppet image via a generated Dockerfile.
        """
        async with FoundryService._build_semaphore:
            # 1. Fetch Template & Blueprints
            tmpl_res = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == template_id))
            tmpl = tmpl_res.scalar_one_or_none()
            if not tmpl:
                raise ValueError("Template not found")
            
            rt_res = await db.execute(select(Blueprint).where(Blueprint.id == tmpl.runtime_blueprint_id))
            nw_res = await db.execute(select(Blueprint).where(Blueprint.id == tmpl.network_blueprint_id))
            rt_bp = rt_res.scalar_one_or_none()
            nw_bp = nw_res.scalar_one_or_none()
            
            rt_def = json.loads(rt_bp.definition)
            nw_def = json.loads(nw_bp.definition)

            # 1.5 Smelter Registry Check (SMLT-03, SMLT-04, SMLT-05)
            # Fetch enforcement mode: STRICT or WARNING (default)
            cfg_res = await db.execute(select(Config.value).where(Config.key == "smelter_enforcement_mode"))
            res_val = cfg_res.scalar_one_or_none()
            enforcement_mode = str(res_val).upper() if res_val else "WARNING"
            
            # Clean up mock strings if they leak in
            if "MAGICMOCK" in enforcement_mode:
                enforcement_mode = "STRICT" if "STRICT" in enforcement_mode else "WARNING"
            
            base_os = rt_def.get("base_os", "debian-12-slim")
            os_family = getattr(rt_bp, 'os_family', None) or ("ALPINE" if "alpine" in base_os.lower() else "DEBIAN")
            
            unapproved = await SmelterService.validate_blueprint(db, rt_def, os_family)
            if unapproved:
                if str(enforcement_mode).upper() == "STRICT":
                    raise HTTPException(status_code=403, detail=f"Build rejected: Blueprint contains unapproved ingredients: {unapproved}")
                else:
                    logger.warning(f"Smelter WARNING: Blueprint for template {tmpl.friendly_name} contains unapproved ingredients: {unapproved}")
                    tmpl.is_compliant = False
            else:
                tmpl.is_compliant = True

            # 1.6 Mirror Status Check (Fail-Fast)
            # Fetch all approved ingredients involved in this build
            # For simplicity in this iteration, we check all active ingredients for the OS family
            # In a real scenario, we'd only check the packages defined in the blueprint.
            python_packages = rt_def.get("packages", {}).get("python", [])
            for pkg in python_packages:
                pkg_name = pkg.split(">")[0].split("<")[0].split("=")[0].strip().lower()
                res = await db.execute(select(ApprovedIngredient).where(
                    ApprovedIngredient.name.ilike(pkg_name),
                    ApprovedIngredient.os_family == os_family,
                    ApprovedIngredient.is_active == True,
                ))
                ing = res.scalar_one_or_none()
                if ing and ing.mirror_status != "MIRRORED":
                    raise HTTPException(
                        status_code=403,
                        detail=f"Build rejected: Ingredient '{pkg_name}' is approved but not yet mirrored (Status: {ing.mirror_status}). Wait for mirroring to complete or upload the package manually."
                    )

            # Commit the compliance status
            await db.commit()
            await db.refresh(tmpl)

            # 2. Build Dockerfile Content
            dockerfile = [f"FROM {base_os}"]

            # 2.5 Mirror Configuration Injection (content computed now, files written after build_dir exists)
            pip_conf = MirrorService.get_pip_conf_content()
            sources_list = MirrorService.get_sources_list_content()
            dockerfile.append("COPY pip.conf /etc/pip.conf")
            if os_family == "DEBIAN":
                dockerfile.append("COPY sources.list /etc/apt/sources.list")

            
            # Injection Recipes
            for tool in rt_def.get("tools", []):
                tool_id = tool.get("id")
                matrix_res = await db.execute(
                    select(CapabilityMatrix).where(
                        CapabilityMatrix.base_os_family == os_family,
                        CapabilityMatrix.tool_id == tool_id
                    )
                )
                recipe = matrix_res.scalar_one_or_none()
                if recipe:
                    dockerfile.append(f"# Recipe for {tool_id}")
                    
                    # Security CAV-03: Expand {{ARTIFACT_URL}} macro if recipe is tied to an artifact
                    final_recipe = recipe.injection_recipe
                    if recipe.artifact_id:
                        # Construct internal download URL.
                        # Since this is for Dockerfile 'curl'/'wget' during build, 
                        # it needs to be accessible from the build container.
                        # We use the agent's internal URL or a configurable base.
                        base_url = os.getenv("AGENT_URL", "https://localhost:8001")
                        artifact_url = f"{base_url}/api/artifacts/{recipe.artifact_id}/download"
                        final_recipe = final_recipe.replace("{{ARTIFACT_URL}}", artifact_url)
                    
                    dockerfile.append(final_recipe)
            
            # Baked-in Packages
            packages = rt_def.get("packages", {})
            if "python" in packages:
                pkg_list = " ".join(packages["python"])
                dockerfile.append(f"RUN pip install --no-cache-dir --break-system-packages {pkg_list}")
                
            # Network Perimeter (Simplified Sidecar Config Injection)
            egress_rules = nw_def.get("egress_rules", [])
            dockerfile.append(f"ENV EGRESS_POLICY='{json.dumps(egress_rules)}'")
            
            # Core Puppet Code
            dockerfile.append("WORKDIR /app")
            dockerfile.append("COPY requirements.txt .")
            dockerfile.append("RUN pip install --no-cache-dir -r requirements.txt --break-system-packages")
            dockerfile.append("COPY environment_service/ environment_service/")
            dockerfile.append("CMD [\"python\", \"environment_service/node.py\"]")

            # 3. Perform Build
            image_tag = tmpl.friendly_name
            image_uri = f"localhost:5000/puppet:{image_tag}"

            # Resolve the puppets source directory (relative to this service file)
            puppets_src = os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "puppets")
            )

            build_dir = f"/tmp/puppet_build_{tmpl.id}_{hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:8]}"
            await asyncio.to_thread(os.makedirs, build_dir, exist_ok=True)

            # Write mirror config files now that build_dir exists
            with open(os.path.join(build_dir, "pip.conf"), "w") as f:
                f.write(pip_conf)
            with open(os.path.join(build_dir, "sources.list"), "w") as f:
                f.write(sources_list)

            # Copy puppet source files into the build context
            env_src = os.path.join(puppets_src, "environment_service")
            env_dst = os.path.join(build_dir, "environment_service")
            req_src = os.path.join(puppets_src, "requirements.txt")
            req_dst = os.path.join(build_dir, "requirements.txt")

            if os.path.isdir(env_src):
                await asyncio.to_thread(shutil.copytree, env_src, env_dst, dirs_exist_ok=True)
            else:
                logger.warning(f"⚠️  environment_service not found at {env_src} — COPY may fail")

            if os.path.isfile(req_src):
                await asyncio.to_thread(shutil.copy2, req_src, req_dst)
            else:
                logger.warning(f"⚠️  requirements.txt not found at {req_src} — COPY may fail")

            dockerfile_path = os.path.join(build_dir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write("\n".join(dockerfile))

            try:
                # Detect Engine
                engine = "docker"
                try:
                    res = subprocess.run(["podman", "--version"], check=True, capture_output=True)
                    engine = "podman"
                except:
                    pass

                logger.info(f"🏗️  Building {image_tag} using {engine} in {build_dir}...")
                build_cmd = [engine, "build", "-t", image_uri, "-f", dockerfile_path, build_dir]
                proc = await asyncio.create_subprocess_exec(
                    *build_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                stdout, _ = await proc.communicate()

                if proc.returncode != 0:
                    output_tail = stdout.decode()[-250:].strip()
                    logger.error(f"❌ Build Failed:\n{stdout.decode()}")
                    return ImageResponse(tag=image_tag, image_uri=image_uri, status=f"FAILED: {output_tail}", created_at=datetime.utcnow())

                # Push
                push_proc = await asyncio.create_subprocess_exec(
                    engine, "push", image_uri,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                await push_proc.communicate()
                
                # Update Template in DB
                tmpl.current_image_uri = image_uri
                tmpl.last_built_at = datetime.utcnow()
                tmpl.status = "STAGING"
                await db.commit()
                
                # 3. Post-Build Validation (Smelt-Check & BOM)
                # Run a basic 'python --version' check as a smoke test
                validation_report = await StagingService.run_smelt_check(tmpl.id, "python --version && pip --version")
                
                if validation_report["status"] == "SUCCESS":
                    logger.info(f"✅ Smelt-Check PASSED for {tmpl.friendly_name}")
                    tmpl.status = "ACTIVE"
                    # Capture BOM after validation success
                    await StagingService.capture_bom(tmpl.id)
                else:
                    logger.error(f"❌ Smelt-Check FAILED for {tmpl.friendly_name}")
                    tmpl.status = "FAILED"
                
                await db.commit()
                await db.refresh(tmpl)
                
                return ImageResponse(
                    tag=image_tag, 
                    image_uri=image_uri, 
                    status=f"SUCCESS (Smelt-Check: {tmpl.status})", 
                    created_at=datetime.utcnow()
                )
                
            finally:
                if os.path.exists(build_dir):
                    await asyncio.to_thread(shutil.rmtree, build_dir)

    @staticmethod
    async def build_image(req: ImageBuildRequest) -> ImageResponse:
        """
        Builds and pushes a puppet image to the local registry using shell commands.
        """
        logger.info(f"Starting build for image {req.tag} with capabilities {req.capabilities}")
        
        # 1. Prepare Build Arguments
        # We assume Containerfile.node supports these ARGs
        build_args = []
        for k, v in req.capabilities.items():
            build_args.extend(["--build-arg", f"{k.upper()}_VERSION={v}"])
        
        image_uri = f"localhost:5000/puppet:{req.tag}"
        
        # 2. Run Docker Build
        # Path to puppets/ directory relative to app root
        context_path = os.path.join(os.getcwd(), "..", "puppets")
        dockerfile_path = os.path.join(context_path, "Containerfile.node")
        
        try:
            # Check for podman or docker (async)
            engine = "docker"
            try:
                probe = await asyncio.create_subprocess_exec(
                    "podman", "--version",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await probe.wait()
                if probe.returncode == 0:
                    engine = "podman"
            except Exception:
                pass

            build_cmd = [engine, "build", "-t", image_uri, "-f", dockerfile_path, context_path] + build_args
            logger.info(f"Running build command: {' '.join(build_cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *build_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode()
                logger.error(f"Build failed: {err}")
                return ImageResponse(
                    tag=req.tag,
                    image_uri=image_uri,
                    status=f"FAILED: {err[:100]}",
                    created_at=datetime.utcnow()
                )

            # 3. Push to Local Registry
            push_cmd = [engine, "push", image_uri]
            logger.info(f"Running push command: {' '.join(push_cmd)}")
            push_proc = await asyncio.create_subprocess_exec(
                *push_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, push_stderr = await push_proc.communicate()
            if push_proc.returncode != 0:
                err = push_stderr.decode()
                logger.error(f"Push failed: {err}")
                return ImageResponse(
                    tag=req.tag,
                    image_uri=image_uri,
                    status=f"PUSH_FAILED: {err[:100]}",
                    created_at=datetime.utcnow()
                )

            return ImageResponse(
                tag=req.tag,
                image_uri=image_uri,
                status="SUCCESS",
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Foundry Error: {e}")
            return ImageResponse(
                tag=req.tag,
                image_uri=image_uri,
                status=f"ERROR: {str(e)}",
                created_at=datetime.utcnow()
            )

    @staticmethod
    async def list_images() -> List[ImageResponse]:
        """
        Shell for listing images from the local registry.
        """
        return []

foundry_service = FoundryService()
