import os
import json
import subprocess
import time
from typing import Literal, Optional
from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

FRAMEWORK_TIMEOUTS = {
    "nextjs": 600,
    "nestjs": 900,
    "laravel": 900,
    "react": 300,
    "vite": 180,
    "express": 180,
    "fastapi": 120,
    "flask": 120,
    "angular": 600,
    "vue": 300,
    "svelte": 180,
    "astro": 180
}

def create_project(
    workspace_root: str,
    framework: Literal["nextjs", "react", "vite", "vue", "angular", "svelte", "astro", "express", "fastapi", "flask", "laravel", "nestjs"],
    language: Literal["javascript", "typescript", "python", "php"] = "javascript",
    package_manager: Literal["npm", "yarn", "pnpm", "composer", "pip"] = "npm",
    template: str = "default",
    timeout: Optional[int] = None
) -> ToolResult:
    """
    Creates an official project scaffold using the framework's recommended CLI.
    
    Use this whenever the user asks to:
    - create a Next.js app
    - create a React app
    - create a Vite app
    - create a FastAPI project
    - create an Express project
    - create a Laravel project
    - create a NestJS project
    
    Never recreate framework boilerplate manually using write_file.
    """
    root_path = resolve_safe_path(workspace_root, ".")
    
    from app.tools.utils import run_with_idle_timeout
    
    phases = []
    
    if framework == "nextjs":
        ts_flag = "--typescript" if language == "typescript" else "--js"
        # Since create-next-app supports --no-install (sometimes --skip-install based on version), 
        # we will just let it install for now, or split it if we knew the exact flag.
        # We will keep it as one phase for Next.js unless we know for sure.
        phases.append({"name": "Scaffold & Install", "cmd": f"npx create-next-app@latest . --yes --eslint --app --src-dir --use-{package_manager} --no-tailwind --import-alias \"@/*\" {ts_flag}"})
        
    elif framework == "vite" or framework == "react":
        tpl = f"react-ts" if language == "typescript" else "react"
        phases.append({"name": "Scaffold", "cmd": f"{package_manager} create vite@latest . --yes -- --template {tpl}"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install"})
        
    elif framework == "vue":
        ts_flag = "--ts" if language == "typescript" else ""
        phases.append({"name": "Scaffold", "cmd": f"{package_manager} create vue@latest . --yes --default {ts_flag}"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install"})
        
    elif framework == "angular":
        phases.append({"name": "Scaffold", "cmd": f"npx -p @angular/cli ng new app-name --directory . --defaults --skip-install"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install"})
        
    elif framework == "svelte":
        phases.append({"name": "Scaffold", "cmd": f"{package_manager} create svelte@latest . --yes"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install"})
        
    elif framework == "astro":
        ts_flag = "--ts strict" if language == "typescript" else ""
        phases.append({"name": "Scaffold & Install", "cmd": f"{package_manager} create astro@latest . --yes -- --template basics --install {ts_flag}"})
        
    elif framework == "express":
        phases.append({"name": "Scaffold", "cmd": f"{package_manager} init -y"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install express"})
        # Generate minimal index.js
        index_content = "const express = require('express');\nconst app = express();\napp.use(express.json());\napp.get('/', (req, res) => res.send('Hello World!'));\napp.listen(3000, () => console.log('Server running on port 3000'));\n"
        with open(os.path.join(root_path, "index.js"), "w") as f:
            f.write(index_content)
            
    elif framework == "fastapi":
        phases.append({"name": "Environment", "cmd": f"python -m venv venv"})
        reqs = "fastapi[all]\nuvicorn\n"
        with open(os.path.join(root_path, "requirements.txt"), "w") as f:
            f.write(reqs)
        
        main_content = "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get(\"/\")\ndef read_root():\n    return {\"Hello\": \"World\"}\n"
        with open(os.path.join(root_path, "main.py"), "w") as f:
            f.write(main_content)
        
        # Windows specific venv activation
        phases.append({"name": "Dependencies", "cmd": f".\\venv\\Scripts\\pip install -r requirements.txt"})
            
    elif framework == "flask":
        phases.append({"name": "Environment", "cmd": f"python -m venv venv"})
        reqs = "flask\n"
        with open(os.path.join(root_path, "requirements.txt"), "w") as f:
            f.write(reqs)
            
        app_content = "from flask import Flask\napp = Flask(__name__)\n\n@app.route(\"/\")\ndef hello():\n    return \"Hello World!\"\n\nif __name__ == \"__main__\":\n    app.run(debug=True)\n"
        with open(os.path.join(root_path, "app.py"), "w") as f:
            f.write(app_content)
            
        phases.append({"name": "Dependencies", "cmd": f".\\venv\\Scripts\\pip install -r requirements.txt"})
            
    elif framework == "laravel":
        phases.append({"name": "Scaffold & Install", "cmd": f"composer create-project laravel/laravel ."})
        
    elif framework == "nestjs":
        phases.append({"name": "Scaffold", "cmd": f"npx -y @nestjs/cli new . --package-manager {package_manager} --skip-git --skip-install"})
        phases.append({"name": "Dependencies", "cmd": f"{package_manager} install"})
        
    else:
        return ToolResult(success=False, error=f"Unsupported framework: {framework}")

    stdout_log = ""
    stderr_log = ""
    
    start_time = time.time()
    cmd_timeout = timeout if timeout is not None else FRAMEWORK_TIMEOUTS.get(framework, 900)
    cmd_timeout = min(cmd_timeout, 1500) # Hard cap at 25 minutes
    
    completed_phases = []
    failed_phases = []
    timeout_occurred = False
    
    for phase in phases:
        cmd = phase["cmd"]
        name = phase["name"]
        try:
            returncode, stdout, stderr, is_idle_timeout = run_with_idle_timeout(
                cmd,
                str(root_path),
                total_timeout=cmd_timeout,
                idle_timeout=120
            )
            stdout_log += f"[{name}] {stdout}\n"
            stderr_log += f"[{name}] {stderr}\n"
            
            if is_idle_timeout:
                timeout_occurred = True
                failed_phases.append(name)
                break
                
            if returncode != 0:
                failed_phases.append(name)
                return ToolResult(success=False, error=f"Phase '{name}' failed with exit code {returncode}:\n{stderr}\n\nSTDOUT:\n{stdout}")
            
            completed_phases.append(name)
        except Exception as e:
            failed_phases.append(name)
            return ToolResult(success=False, error=f"Execution error on '{name}': {str(e)}")
            
    elapsed_time = int(time.time() - start_time)
            
    # List created files
    created_files_list = []
    has_package_json = False
    has_node_modules = False
    
    for root, dirs, files in os.walk(root_path):
        if "node_modules" in dirs:
            has_node_modules = True
            dirs.remove("node_modules")
        if ".git" in dirs:
            dirs.remove(".git")
        if "venv" in dirs:
            dirs.remove("venv")
            
        for file in files:
            if file == "package.json":
                has_package_json = True
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, root_path)
            created_files_list.append(rel_path)
            
    # If timeout occurred but we have core project files, treat as partial success
    if timeout_occurred:
        if has_package_json or len(created_files_list) > 5:
            success = True
            msg = f"Scaffold partially completed (timed out after {cmd_timeout}s but files exist)."
        else:
            return ToolResult(success=False, error=f"Command timed out after {cmd_timeout}s and no files were created.")
    else:
        success = True
        msg = f"Successfully scaffolded {framework} project."
        
    output_meta = {
        "status": "partial_success" if timeout_occurred else "success",
        "completed_phases": completed_phases,
        "failed_phases": failed_phases,
        "workspace_ready": len(completed_phases) > 0,
        "framework": framework,
        "package_manager": package_manager,
        "project_root": workspace_root,
        "install_time_seconds": elapsed_time,
        "created_files": created_files_list[:20],
        "total_files": len(created_files_list)
    }
    
    return ToolResult(
        success=success,
        output=f"{msg}\nMetadata: {json.dumps(output_meta, indent=2)}\n\n(Truncated Output)\nSTDOUT:\n{stdout_log[:1000]}\nSTDERR:\n{stderr_log[:1000]}",
        data=output_meta
    )
