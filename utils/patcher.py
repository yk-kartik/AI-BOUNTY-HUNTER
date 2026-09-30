import logging
import os
import re

logger = logging.getLogger(__name__)

PATCH_BLOCK_PATTERN = re.compile(
    r"<<<< SEARCH\s*\n(.*?)\n====\s*\n(.*?)\n>>>> REPLACE",
    re.DOTALL,
)


def apply_patch(target_file_path, patch_content):
    if not os.path.isfile(target_file_path):
        logger.error("Target file %s not found.", target_file_path)
        return False

    if not patch_content or not patch_content.strip():
        logger.error("Patch content is empty.")
        return False

    file_headers = re.findall(r"(?im)^FILE:\s*([^\n]+)$", patch_content)
    if len(file_headers) != 1:
        logger.error("Patch must contain exactly one FILE header.")
        return False

    blocks = PATCH_BLOCK_PATTERN.findall(patch_content)
    if not blocks:
        logger.error("No SEARCH/REPLACE blocks found in patch.")
        return False

    try:
        with open(target_file_path, "r", encoding="utf-8") as file:
            original_code = file.read()
    except OSError as exc:
        logger.error("Could not read target file: %s", exc)
        return False

    modified_code = original_code.replace("\r\n", "\n")

    for search_text, replace_text in blocks:
        if any(
            marker in search_text or marker in replace_text
            for marker in ("...", "//...", "// ...", "# ...", "/* ...")
        ):
            logger.error("Patch contains unsupported placeholder markers.")
            return False

        search_text = search_text.replace("\r\n", "\n").strip("\n")
        replace_text = replace_text.replace("\r\n", "\n").strip("\n")

        if not search_text:
            logger.error("SEARCH block is empty.")
            return False

        exact_count = modified_code.count(search_text)
        if exact_count == 1:
            modified_code = modified_code.replace(search_text, replace_text, 1)
            continue

        if exact_count > 1:
            logger.error("SEARCH block matched multiple locations.")
            return False

        escaped_lines = [re.escape(line.strip()) for line in search_text.split("\n") if line.strip()]
        flexible_pattern = r"\s+".join(escaped_lines)
        matches = list(re.finditer(flexible_pattern, modified_code))

        if len(matches) != 1:
            logger.error("Flexible SEARCH block matched %d locations.", len(matches))
            return False

        match = matches[0]
        modified_code = modified_code[:match.start()] + replace_text + modified_code[match.end():]

    try:
        with open(target_file_path, "w", encoding="utf-8", newline="") as file:
            file.write(modified_code)
    except OSError as exc:
        logger.error("Could not write target file: %s", exc)
        return False

    logger.info("File %s successfully updated.", target_file_path)
    return True
