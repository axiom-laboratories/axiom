import logging
import os
import subprocess
import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.future import select
from ..db import Blueprint, PuppetTemplate, CapabilityMatrix, AsyncSession
from ..models import ImageBuildRequest, ImageResponse

logger = logging.getLogger(__name__)

class FoundryService:
    @staticmethod
    async def build_template(template_id: str, db: AsyncSession) -> ImageResponse:
        """
        Stitches Blueprints into a single Puppet image via a generated Dockerfile.
        """
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
        
        # 2. Build Dockerfile Content
        base_os = rt_def.get("base_os", "debian-12-slim")
        os_family = "DEBIAN" # Simplified detection
        
        dockerfile = [f"FROM {base_os}"]
        
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
                dockerfile.append(recipe.injection_recipe)
        
        # Baked-in Packages
        packages = rt_def.get("packages", {})
        if "python" in packages:
            pkg_list = " ".join(packages["python"])
            dockerfile.append(f"RUN pip install --no-cache-dir --break-system-packages {pkg_list}")
            
        # Network Perimeter (Simplified Sidecar Config Injection)
        egress_rules = nw_def.get("egress_rules", [])
        dockerfile.append(f"ENV EGRESS_POLICY='{json.dumps(egress_rules)}'")
        
        # Core Puppet Code (Assumed relative path)
        context_path = "/app/puppets"
        dockerfile.append("WORKDIR /app")
        dockerfile.append("COPY environment_service/node.py .")
        dockerfile.append("CMD [\"python\", \"node.py\"]")
        
        # 3. Perform Build
        image_tag = tmpl.friendly_name
        image_uri = f"localhost:5000/puppet:{image_tag}"
        
        build_dir = f"/app/temp_build_{tmpl.id}"
        os.makedirs(build_dir, exist_ok=True)
        with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
            f.write("\n".join(dockerfile))
            
        try:
            # Detect Engine
            engine = "docker"
            try:
                subprocess.run(["podman", "--version"], check=True, capture_output=True)
                engine = "podman"
            except:
                pass

            logger.info(f"🏗️  Building {image_tag} using {engine}...")
            build_cmd = [engine, "build", "-t", image_uri, "-f", os.path.join(build_dir, "Dockerfile"), context_path]
            res = subprocess.run(build_cmd, capture_output=True, text=True)
            
            if res.returncode != 0:
                logger.error(f"❌ Build Failed Output:\n{res.stdout}\n{res.stderr}")
                return ImageResponse(tag=image_tag, image_uri=image_uri, status=f"FAILED: See Logs", created_at=datetime.utcnow())

            # Push
            push_cmd = [engine, "push", image_uri]
            subprocess.run(push_cmd, capture_output=True, text=True)
            
            # Update Template in DB
            tmpl.current_image_uri = image_uri
            await db.commit()
            
            return ImageResponse(tag=image_tag, image_uri=image_uri, status="SUCCESS", created_at=datetime.utcnow())
            
        finally:
             import shutil
             if os.path.exists(build_dir):
                 shutil.rmtree(build_dir)

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
            # Check for podman or docker
            engine = "docker"
            try:
                subprocess.run(["podman", "--version"], check=True, capture_output=True)
                engine = "podman"
            except:
                pass

            build_cmd = [engine, "build", "-t", image_uri, "-f", dockerfile_path, context_path] + build_args
            logger.info(f"Running build command: {' '.join(build_cmd)}")
            
            res = subprocess.run(build_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Build failed: {res.stderr}")
                return ImageResponse(
                    tag=req.tag,
                    image_uri=image_uri,
                    status=f"FAILED: {res.stderr[:100]}",
                    created_at=datetime.utcnow()
                )

            # 3. Push to Local Registry
            push_cmd = [engine, "push", image_uri]
            logger.info(f"Running push command: {' '.join(push_cmd)}")
            res = subprocess.run(push_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Push failed: {res.stderr}")
                return ImageResponse(
                    tag=req.tag,
                    image_uri=image_uri,
                    status=f"PUSH_FAILED: {res.stderr[:100]}",
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
