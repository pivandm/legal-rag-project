import os


def resolve_output_path(relative_path_from_project_root):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(
        os.path.join(script_dir, "..", relative_path_from_project_root)
    )
