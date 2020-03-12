import sgtk
import os

def get_unlisted_resources(file_extension, shelf_subdir, shelf_names=None):
    resources = {}
    engine = sgtk.platform.current_engine()
    all_shelves = engine.app.get_shelves()
    shelves = {}

    if (shelf_names):
        for shelf_name in shelf_names:
            shelves[shelf_name] = all_shelves[shelf_name]
    else:
        shelves = all_shelves

    for shelf_name, shelf_path in shelves.items():
        resource_dir = os.path.join(shelf_path, shelf_subdir)
        if not os.path.exists(resource_dir):
            continue
        files = os.listdir(resource_dir)

        for f in files:
            full_path = os.path.join(resource_dir, f)
            if os.path.isdir(full_path):
                continue

            comps = f.split(".")
            ext = comps[-1]
            if ext == file_extension:
                resources[comps[0]] = full_path
    
    return resources
