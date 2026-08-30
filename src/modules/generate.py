
from pathlib import Path
import sys

FILES = {
    "__init__.py": "",
    "model.py": "",
    "schema.py": "",
    "repository.py": "",
    "service.py": "",
    "router.py": "",
}


def create_module(module_name: str, base_dir: str = "src/modules"):
    module_path = Path(base_dir) / module_name

    if module_path.exists():
        print(f"❌ Module '{module_name}' already exists.")
        return

    module_path.mkdir(parents=True)

    for filename, content in FILES.items():
        (module_path / filename).write_text(content)

    print(f"✅ Module '{module_name}' created successfully!")
    print(f"\nStructure:")
    print(f"{base_dir}/")
    print(f"    └── {module_name}/")
    for file in FILES:
        print(f"        ├── {file}")


if __name__ == "__main__":
    module_name = input("Enter module name: ").strip()

    if not module_name:
        print("Module name cannot be empty.")
        sys.exit(1)

    create_module(module_name)