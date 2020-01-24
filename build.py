#!/usr/bin/env python3

from argparse import ArgumentParser
from argparse import REMAINDER
from glob import glob
from pathlib import Path
import subprocess
from typing import List, Optional
from xml.etree import ElementTree

class ConfigNotFoundException(Exception):
  pass

class InvalidPackageXmlException(Exception):
  pass

class LogsNotFoundException(Exception):
  pass

def find_logs() -> Optional[Path]:
  cwd = Path.cwd()
  logs = cwd / 'log'

  if logs.exists():
    return logs

  current = cwd
  parent = current.parent

  while not logs.exists() and current != parent:
    current = parent
    parent = current.parent
    logs = current / 'log'

  if logs.exists():
    return logs
  else:
    return None

def get_package_name(packages_xml: Path) -> str:
  tree = ElementTree.parse(str(packages_xml))
  root = tree.getroot()
  package_name = root.find('name').text

  if package_name != None:
    return package_name
  else:
    raise InvalidPackageXmlException()

def find_package_names() -> List[str]:
  packages = glob('**/package.xml', recursive=True)
  package_names: List[str] = []

  for package in packages:
    package_names.append(get_package_name(Path(package)))

  return package_names

def main():
  parser = ArgumentParser()
  parser.add_argument('-v', '--verbose', action='store_true', help='Enables verbose build')
  parser.add_argument('-d', '--dry_run', action='store_true', help='Prints the command without running it')
  parser.add_argument('packages', type=str, nargs=REMAINDER)
  args = parser.parse_args()

  is_package = Path('package.xml').exists()
  is_workspace = False
  ws_logs = find_logs()

  if not ws_logs:
    raise LogsNotFoundException()

  ws_dir = ws_logs.parent

  colcon_args = ['colcon', 'build']
  packages: List[str] = args.packages

  if not packages:
    if is_package:
      packages.append(get_package_name(Path('package.xml')))
    else:
      packages.extend(find_package_names())

  if args.verbose:
    colcon_args.append('--event-handlers')
    colcon_args.append('console_direct+')

  can_use_packages_select: bool = False
  if ws_logs is not None:
    latest = ws_logs / 'latest' / 'logger_all.log'

    if latest.exists():
      last_command: str = ''

      with latest.open() as log_file:
        last_command = log_file.readline()

      can_use_packages_select = True
      for package in packages:
        if not package in last_command:
          print("package %s not in %s" % (package, last_command))
          can_use_packages_select = False
          break

  if can_use_packages_select:
    colcon_args.append('--packages-select')
  else:
    colcon_args.append('--packages-up-to')

  for package in packages:
    colcon_args.append(package)

  flattened_command = ' '.join(colcon_args)
  if args.dry_run:
    print("cwd=%s cmd=%s" % (ws_dir, flattened_command))
  else:
    subprocess.Popen(colcon_args, cwd=ws_dir)

if __name__ == "__main__":
  main()
  