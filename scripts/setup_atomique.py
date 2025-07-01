import os
import requests
import zipfile
import shutil
import subprocess
import sys
import logging

logger = logging.getLogger("evaluation.setup")

def download_and_extract(url: str, target_dir: str, archive_name: str, expected_extracted_dir: str):

    logger.info(f"Downloading {archive_name} from {url}...")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        archive_path = os.path.join(target_dir, archive_name)
        
        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("Download complete.")

        logger.info(f"Extracting {archive_name} to {target_dir}...")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        logger.info("Extraction complete.")

        os.remove(archive_path)

        os.rename(
            os.path.join(target_dir, archive_name.replace('.zip', '')),
            os.path.join(target_dir, expected_extracted_dir)
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        sys.exit(1)
    except zipfile.BadZipFile:
        logger.error(f"Error: Downloaded file '{archive_name}' is not a valid zip file.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during download/extraction: {e}")
        sys.exit(1)
'''
def compile_software(source_dir: str, build_commands: list[list[str]], expected_output_file: str):
    """
    Compiles the software using a series of shell commands.

    Args:
        source_dir (str): The directory where the compilation commands should be run.
        build_commands (list[list[str]]): A list of command-line arguments. Each inner list
            represents a single command (e.g., [['make', 'clean'], ['make']]).
        expected_output_file (str, optional): The name of a file expected to be
            generated after successful compilation. Used for verification. Defaults to None.
    """
    print(f"Compiling software in: {source_dir}")
    original_cwd = os.getcwd()
    try:
        os.chdir(source_dir) # Change to the source directory for compilation

        for command_set in build_commands:
            print(f"Executing command: {' '.join(command_set)}")
            result = subprocess.run(command_set, check=True, capture_output=True, text=True, shell=False)
            print(result.stdout)
            if result.stderr:
                print(f"Stderr (if any):\n{result.stderr}")
        print("Compilation successful.")

        if expected_output_file:
            if not os.path.exists(expected_output_file):
                print(f"Warning: Expected output file '{expected_output_file}' not found after compilation in '{source_dir}'.", file=sys.stderr)
            else:
                print(f"Compiled executable found: {os.path.join(source_dir, expected_output_file)}")

    except subprocess.CalledProcessError as e:
        print(f"Error during compilation (command: {' '.join(e.cmd)}):", file=sys.stderr)
        print(f"Stdout:\n{e.stdout}", file=sys.stderr)
        print(f"Stderr:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: Build tool not found. Make sure '{e.filename}' is installed and in your system's PATH.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during compilation: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        os.chdir(original_cwd)
'''

def main():

    baselines = {
        'atomique': {
            'ZIP_FILE_NAME': "fpqa-revision-AE.zip",
            'URL': "https://zenodo.org/records/10995324/files/fpqa-revision-AE.zip?download=1",
            'BASELINE_NAME': "atomique",
            'BASELINE_TARGET_DIR': os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'baselines', 'atomique'),
            'BASELINE_ROOT_DIR': os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'baselines'),
            }}

    for info in baselines.values():
        
        logger.info(f"--- Starting setup ---")

        if os.path.exists(info['BASELINE_TARGET_DIR']):
            shutil.rmtree(info['BASELINE_TARGET_DIR'])  # Clean up any previous attempts

        download_and_extract(info['URL'], info['BASELINE_ROOT_DIR'], info['ZIP_FILE_NAME'], info['BASELINE_NAME'])

        logger.info(f"--- Baseline '{info['BASELINE_NAME']}' setup complete ---")

if __name__ == "__main__":
    main()
