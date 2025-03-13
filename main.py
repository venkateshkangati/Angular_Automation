from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import shutil
from pathlib import Path

app = FastAPI()

class ProjectConfig(BaseModel):
    project_name: str
    modules: list[str]

GITHUB_REPO_URL = "https://github.com/venkateshkangati/lazy-loading-project.git"
PROJECT_DIR = Path("./projects")
PROJECT_DIR.mkdir(exist_ok=True)

@app.post("/customize-project/")
def customize_project(config: ProjectConfig):
    project_path = PROJECT_DIR / config.project_name

    # Check if project already exists
    if project_path.exists():
        shutil.rmtree(project_path)

    # Clone the GitHub repo
    try:
        subprocess.run(["git", "clone", GITHUB_REPO_URL, str(project_path)], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone the repository: {str(e)}")

    # Handle renaming the project folder if necessary
    actual_project_path = project_path / "lazy-loading-project"
    if actual_project_path.exists():
        shutil.move(str(actual_project_path), str(project_path))

    # Update project name in angular.json and package.json
    angular_json_path = project_path / "angular.json"
    package_json_path = project_path / "package.json"
    app_routing_path = project_path / "src/app/app-routing.module.ts"
    app_component_html_path = project_path / "src/app/app.component.html"

    try:
        for file_path in [angular_json_path, package_json_path]:
            if file_path.exists():
                content = file_path.read_text()
                content = content.replace("lazy-loading-project", config.project_name)
                file_path.write_text(content)

        # Remove unselected modules
        modules_path = project_path / "src/app"
        if modules_path.exists():
            for module in modules_path.iterdir():
                if module.is_dir() and module.name not in config.modules:
                    shutil.rmtree(module)

        # Remove unselected module imports in app-routing.module.ts
        if app_routing_path.exists():
            routing_content = app_routing_path.read_text()
            updated_lines = []

            for line in routing_content.splitlines():
                if "loadChildren" in line:
                    module_name = line.split("import('./")[1].split("/")[0] if "import('./" in line else ""
                    if module_name not in config.modules:
                        continue  # Skip the line if the module is unselected
                updated_lines.append(line)

            # Write the updated routing content back
            app_routing_path.write_text("\n".join(updated_lines))

        # Remove unselected module links in app.component.html
        if app_component_html_path.exists():
            html_content = app_component_html_path.read_text()
            updated_html_lines = []

            for line in html_content.splitlines():
                if 'routerLink' in line:
                    module_name = line.split('routerLink="/')[1].split('"')[0] if 'routerLink="/' in line else ""
                    if module_name not in config.modules:
                        continue  # Skip the line if the module is unselected
                updated_html_lines.append(line)

            # Write the updated HTML content back
            app_component_html_path.write_text("\n".join(updated_html_lines))

    except Exception as e:
        shutil.rmtree(project_path)  # Clean up on failure
        raise HTTPException(status_code=500, detail=f"Project customization failed: {str(e)}")

    return {
        "message": "Project customized successfully",
        "project_path": str(project_path),
        "selected_modules": config.modules
    }
