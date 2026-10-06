#!/usr/bin/env python3
"""
Sorts generated files by band prefix (CB1, CB2, ..., VB1, VB2, ...) into
per-band folders. The list of prefixes is read from material_config.json
(produced_band_files, written by Kohn-Sham-States-Extraction.py) so it
adapts automatically to however many bands were requested, instead of a
hardcoded 6-band mapping.

Unmodified from the validated one-off toolkit.
"""

import os
import shutil
import sys
import json


def build_prefix_mappings():
    if not os.path.exists("material_config.json"):
        print("ERROR: material_config.json not found. Run Detect-Configuration.py "
              "or Manual-Configuration.py first.")
        sys.exit(1)

    with open("material_config.json") as f:
        config = json.load(f)

    produced = config.get("produced_band_files")
    if not produced:
        print("ERROR: material_config.json has no produced_band_files. "
              "Run Kohn-Sham-States-Extraction.py first.")
        sys.exit(1)

    mapping = {}
    for filename in produced:
        folder_name = os.path.splitext(filename)[0]  # e.g. "CB1-Conduction-Band"
        prefix = folder_name.split("-")[0] + "-"       # e.g. "CB1-"
        mapping[prefix] = folder_name
    return mapping


def create_folders(base_dir, prefix_mappings):
    created_folders = []
    for prefix, folder_name in prefix_mappings.items():
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            created_folders.append(folder_name)
            print(f"✓ Created folder: {folder_name}")
        else:
            print(f"• Folder already exists: {folder_name}")
    return created_folders


def organize_files(base_dir, prefix_mappings):
    moved_files = {prefix: [] for prefix in prefix_mappings.keys()}
    skipped_files = []

    all_files = [f for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
    all_files = [f for f in all_files if not f.endswith('.py')]

    print(f"\nFound {len(all_files)} files to process...\n")

    for filename in all_files:
        moved = False
        # Longest prefix first so e.g. "CB10-" doesn't get matched by "CB1-"
        for prefix, folder_name in sorted(prefix_mappings.items(), key=lambda kv: -len(kv[0])):
            if filename.startswith(prefix):
                src_path = os.path.join(base_dir, filename)
                dest_folder = os.path.join(base_dir, folder_name)
                dest_path = os.path.join(dest_folder, filename)
                try:
                    shutil.move(src_path, dest_path)
                    moved_files[prefix].append(filename)
                    print(f"✓ Moved: {filename} → {folder_name}/")
                    moved = True
                    break
                except Exception as e:
                    print(f"✗ Error moving {filename}: {e}")
                    skipped_files.append(filename)
                    moved = True
                    break

        if not moved:
            skipped_files.append(filename)

    return moved_files, skipped_files


def print_summary(prefix_mappings, moved_files, skipped_files):
    print("\n" + "="*70)
    print("ORGANIZATION SUMMARY")
    print("="*70)

    total_moved = 0
    for prefix, folder_name in prefix_mappings.items():
        count = len(moved_files[prefix])
        total_moved += count
        print(f"\n{folder_name}:")
        print(f"  Files moved: {count}")
        if 0 < count <= 10:
            for f in moved_files[prefix]:
                print(f"    - {f}")

    print(f"\n{'='*70}")
    print(f"Total files moved: {total_moved}")

    if skipped_files:
        print(f"Files skipped (no matching prefix): {len(skipped_files)}")
        if len(skipped_files) <= 10:
            for f in skipped_files:
                print(f"  - {f}")

    print("="*70 + "\n")


def main():
    current_dir = os.getcwd()

    print("="*70)
    print("FILE ORGANIZATION BY PREFIX")
    print("="*70)
    print(f"Working directory: {current_dir}\n")

    prefix_mappings = build_prefix_mappings()

    print("Creating folders...")
    create_folders(current_dir, prefix_mappings)

    print("\nOrganizing files...")
    moved_files, skipped_files = organize_files(current_dir, prefix_mappings)

    print_summary(prefix_mappings, moved_files, skipped_files)

    print("✓ Organization complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
        sys.exit(1)
