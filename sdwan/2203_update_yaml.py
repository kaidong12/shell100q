"""
YAML - Python parser
https://www.w3schools.io/file/yaml-python-read-write/

yaml is a superset of json. It contains key and value pairs with included indentation and tabs.

python3 -m pip search yaml
python3 -m pip install pyyaml
python3 -m pip install ruamel.yaml

To run this script:
python3 2203_update_yaml.py styx-vtest_1G
python3 2203_update_yaml.py hydra-vtest_10G

review:
    2025-11-24
    2026-01-01

"""

from pathlib import Path
from datetime import datetime
from ruamel.yaml import YAML
import argparse
import logging

# --------------------
# Logging
# --------------------


def setup_logging(path: str) -> logging.Logger:
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)
    logfile = LOG_DIR / f"{path}_{datetime.now():%Y%m%d_%H%M%S}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


# --------------------
# YAML helpers
# --------------------

ryaml = YAML()
ryaml.preserve_quotes = True
ryaml.indent(sequence=4, offset=2)
ryaml.width = 200


def read_yaml(file: str):
    with open(file, "r", encoding="utf-8") as f:
        return ryaml.load(f)


def write_yaml(file: str, data):
    with open(file, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)


# --------------------
# Core logic
# --------------------


def update_yaml(yaml_file: Path, bindings: dict, logger: logging.Logger):
    config = read_yaml(yaml_file)

    machines = config.get("machines")
    if not machines or "pm5" not in machines:
        logger.warning(f"{yaml_file}: pm5 not found!!!")
        return

    pm5 = machines["pm5"]
    interfaces = pm5.get("interfaces", {})

    for _, interface in interfaces.items():
        vnet = interface.get("vnet")

        if vnet not in bindings:
            logger.warning(f"{interface} | vnet={vnet} not in bindings!")
            continue

        intf = bindings[vnet][0]
        interface["intf"][1] = intf

        if bindings[vnet][-1] == "l2_vlan":
            interface["type"] = "l2_vlan"
            logger.info(f"vnet = {vnet:<5} -> {intf:<25} --> l2_vlan")
        else:
            interface.pop("type", None)
            logger.info(f"vnet = {vnet:<5} -> {intf:<25}")
    if "chassis_num" in pm5:
        pm5["chassis_num"] = bindings["chassis_num"]
        logger.info(f"chassis_num -> {bindings['chassis_num']}")

    if "serial_num" in pm5:
        pm5["serial_num"] = bindings["serial_num"]
        logger.info(f"serial_num  -> {bindings['serial_num']}")
    write_yaml(yaml_file, config)
    logger.info(f"done!")


# --------------------
# main()
# --------------------


def main():
    parser = argparse.ArgumentParser(description="Update YAML interface bindings")
    parser.add_argument(
        "path",
        choices=["hydra-vtest_FCV1", "styx-vtest", "hydra-vtest_10G", "styx-vtest_1G"],
        help="path to yaml files",
    )
    args = parser.parse_args()

    logger = setup_logging(args.path)

    logger.info(f"path: {args.path}".center(80, "="))

    bindings = read_yaml(f"{args.path}.yaml")["vlan_binding"]
    for file in Path(args.path).iterdir():
        if file.is_file() and file.suffix == ".yaml":
            logger.info(str(file).center(80, "-"))
            update_yaml(file, bindings, logger)


# --------------------
# Entry point
# --------------------

if __name__ == "__main__":
    main()
