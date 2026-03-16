import logging
import asyncio
import os
import json
import uuid
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..db import PuppetTemplate, ImageBOM, PackageIndex, AsyncSessionLocal

logger = logging.getLogger(__name__)

class StagingService:
    @staticmethod
    async def run_smelt_check(template_id: str, validation_cmd: str) -> dict:
        """
        Runs a post-build validation in an ephemeral container.
        Returns a report with status and logs.
        """
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == template_id))
            tmpl = res.scalar_one_or_none()
            if not tmpl or not tmpl.current_image_uri:
                return {"status": "ERROR", "error": "Image not found"}

            container_name = f"smelt-check-{uuid.uuid4().hex[:8]}"
            # Resource limits: 512MB RAM, 0.5 CPU
            cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "--memory", "512m",
                "--cpus", "0.5",
                tmpl.current_image_uri,
                "sh", "-c", validation_cmd
            ]

            logger.info(f"Smelt-Check: Running validation for {tmpl.friendly_name}...")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await proc.communicate()
            
            is_success = proc.returncode == 0
            report = {
                "status": "SUCCESS" if is_success else "FAILED",
                "exit_code": proc.returncode,
                "logs": stdout.decode()
            }
            
            logger.info(f"Smelt-Check result: {report['status']}")
            return report

    @staticmethod
    async def capture_bom(template_id: str) -> Optional[dict]:
        """
        Executes package discovery inside the image and stores the BOM.
        """
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == template_id))
            tmpl = res.scalar_one_or_none()
            if not tmpl or not tmpl.current_image_uri:
                return None

            logger.info(f"BOM: Capturing materials for {tmpl.friendly_name}...")
            
            # Capture PIP packages
            pip_cmd = ["docker", "run", "--rm", tmpl.current_image_uri, "pip", "list", "--format", "json"]
            p_pip = await asyncio.create_subprocess_exec(*pip_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            pip_out, _ = await p_pip.communicate()
            
            # Capture System packages (APT)
            apt_cmd = ["docker", "run", "--rm", tmpl.current_image_uri, "dpkg-query", "-W", "-f", '${Package}==${Version}\\n']
            p_apt = await asyncio.create_subprocess_exec(*apt_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            apt_out, _ = await p_apt.communicate()

            try:
                pip_data = json.loads(pip_out.decode()) if p_pip.returncode == 0 else []
            except:
                pip_data = []
            
            apt_data = []
            if p_apt.returncode == 0:
                for line in apt_out.decode().splitlines():
                    if "==" in line:
                        name, ver = line.split("==")
                        apt_data.append({"name": name, "version": ver})

            full_bom = {
                "pip": pip_data,
                "apt": apt_data
            }

            # 1. Store Raw BOM
            bom_id = str(uuid.uuid4())
            new_bom = ImageBOM(
                id=bom_id,
                template_id=template_id,
                raw_data_json=json.dumps(full_bom)
            )
            db.add(new_bom)

            # 2. Populate Search Index
            # Clear old index entries for this template
            from sqlalchemy import delete
            await db.execute(delete(PackageIndex).where(PackageIndex.template_id == template_id))
            
            for p in pip_data:
                db.add(PackageIndex(
                    id=str(uuid.uuid4()),
                    template_id=template_id,
                    name=p.get("name"),
                    version=p.get("version"),
                    type="pip"
                ))
            
            for a in apt_data:
                db.add(PackageIndex(
                    id=str(uuid.uuid4()),
                    template_id=template_id,
                    name=a.get("name"),
                    version=a.get("version"),
                    type="apt"
                ))

            tmpl.bom_captured = True
            await db.commit()
            logger.info(f"BOM: Captured {len(pip_data)} pip and {len(apt_data)} apt packages.")
            return full_bom
