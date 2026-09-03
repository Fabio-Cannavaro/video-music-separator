from __future__ import annotations

import argparse
import csv
from pathlib import Path


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def remove_distribution(site_packages: Path, distribution: str) -> list[Path]:
    normalized = distribution.lower().replace("-", "_")
    candidates = [
        item
        for item in site_packages.glob("*.dist-info")
        if item.name.lower().replace("-", "_").startswith(normalized + "_")
        or item.name.lower().replace("-", "_").startswith(normalized + "-")
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"{distribution} dist-info를 하나로 특정하지 못했습니다: "
            f"{[item.name for item in candidates]}"
        )
    dist_info = candidates[0]
    record = dist_info / "RECORD"
    if not record.is_file():
        raise FileNotFoundError(f"RECORD를 찾을 수 없습니다: {record}")

    targets: list[Path] = []
    with record.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if not row:
                continue
            target = site_packages / Path(row[0].replace("/", "\\"))
            if not within(target, site_packages):
                raise RuntimeError(f"site-packages 밖의 경로는 제거하지 않습니다: {target}")
            targets.append(target)

    removed: list[Path] = []
    for target in targets:
        if target.is_file() or target.is_symlink():
            target.unlink()
            removed.append(target)

    for directory in sorted(site_packages.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                pass
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="복제된 Python 런타임에서 배포 단위를 제거")
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--distribution", required=True)
    args = parser.parse_args()
    removed = remove_distribution(args.site_packages.resolve(), args.distribution)
    print(f"{args.distribution}: 파일 {len(removed)}개 제거 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
