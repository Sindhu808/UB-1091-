import os
import zipfile

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        # Exclude massive dependency folders and git/cache files
        dirs[:] = [d for d in dirs if d not in ('node_modules', 'venv', '.git', '__pycache__', '.pytest_cache', 'dist')]
        
        for file in files:
            if not file.endswith(('.pyc', '.env')):
                file_path = os.path.join(root, file)
                # Ensure we don't zip the zip file itself
                if file_path != ziph.filename:
                    # arcname is the relative path inside the zip file
                    arcname = os.path.relpath(file_path, os.path.join(path, '..'))
                    ziph.write(file_path, arcname)

if __name__ == '__main__':
    project_root = r"c:\Users\vijay\OneDrive\Desktop\hack"
    zip_path = r"c:\Users\vijay\OneDrive\Desktop\HELIX_Clean_Code_For_GitHub.zip"
    
    print(f"Creating clean zip file at {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir(project_root, zipf)
    print("Done! Ready for GitHub upload.")
