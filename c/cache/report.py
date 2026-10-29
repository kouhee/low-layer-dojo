#!/usr/bin/env python3
"""Explain Cachegrind cache counters in beginner-friendly Japanese."""

import sys
from pathlib import Path

REQUIRED_EVENTS = ("Dr", "Dw", "D1mr", "D1mw", "DLmr", "DLmw")


def read_summary(path: Path) -> dict[str, int]:
    events: list[str] | None = None
    summary: list[int] | None = None

    with path.open(encoding="utf-8") as report_file:
        for line in report_file:
            if line.startswith("events:"):
                events = line.split()[1:]
            elif line.startswith("summary:"):
                summary = [int(value.replace(",", "")) for value in line.split()[1:]]

    if events is None or summary is None or len(events) != len(summary):
        raise ValueError(f"{path}: events/summary の記録がないか、形式が不正です")

    counts = dict(zip(events, summary))
    missing = [event for event in REQUIRED_EVENTS if event not in counts]
    if missing:
        raise ValueError(f"{path}: 必要なカウンターがありません: {', '.join(missing)}")
    return counts


def percentage(part: int, total: int) -> float:
    return 100.0 * part / total if total else 0.0


def label_for(path: Path) -> str:
    if path.name.endswith(".row"):
        return "行優先 (row)"
    if path.name.endswith(".column"):
        return "列優先 (column)"
    return path.name


def report(path: Path) -> tuple[float, float]:
    counts = read_summary(path)

    d1_accesses = counts["Dr"] + counts["Dw"]
    d1_misses = counts["D1mr"] + counts["D1mw"]
    d1_hits = d1_accesses - d1_misses
    ll_misses = counts["DLmr"] + counts["DLmw"]
    ll_hits = d1_misses - ll_misses

    d1_hit_rate = percentage(d1_hits, d1_accesses)
    ll_hit_rate = percentage(ll_hits, d1_misses)

    print(f"\n【{label_for(path)}】")
    print("D1: CPUに近い、小さくて速いデータキャッシュ")
    print(f"  データを参照した回数: {d1_accesses:,} 回")
    print(f"  D1で見つかった回数:  {d1_hits:,} 回 ({d1_hit_rate:.2f}%)")
    print(f"  D1で見つからない回数: {d1_misses:,} 回 ({100.0 - d1_hit_rate:.2f}%)")
    print("  → D1ヒット率は、高いほど近くのキャッシュで見つかったという意味です。")

    print("LL: D1で見つからないデータを次に探す、より大きなキャッシュ")
    print(
        f"  D1ミス {d1_misses:,} 回のうち、LLで見つかった回数: {ll_hits:,} 回 ({ll_hit_rate:.2f}%)"
    )
    print(f"  LLでも見つからなかった回数: {ll_misses:,} 回")
    print(
        "  → LLでも見つからない場合は、さらに遅いメモリまで取りに行く必要があります。"
    )

    return d1_hit_rate, ll_hit_rate


def explain_comparison(results: dict[str, tuple[float, float]]) -> None:
    if "row" not in results or "column" not in results:
        return

    row_d1, row_ll = results["row"]
    column_d1, column_ll = results["column"]
    difference = row_d1 - column_d1

    print("\n【今回の比較】")
    print(f"  行優先のD1ヒット率: {row_d1:.2f}%")
    print(f"  列優先のD1ヒット率: {column_d1:.2f}%")
    if difference > 0:
        print(
            f"  → 今回は行優先の方が、D1ヒット率が {difference:.2f} ポイント高くなりました。"
        )
    elif difference < 0:
        print(
            f"  → 今回は列優先の方が、D1ヒット率が {-difference:.2f} ポイント高くなりました。"
        )
    else:
        print("  → 2つの走査のD1ヒット率は同じでした。")

    print(
        "  行優先は隣り合う値を順に読むため、同じキャッシュラインのデータを使いやすい走査です。"
    )
    print(
        "  列優先は大きく離れた位置を順に読むため、今回のキャッシュ設定ではD1ミスが増えやすくなります。"
    )
    print(f"  LLヒット率は行優先 {row_ll:.2f}%、列優先 {column_ll:.2f}% です。")
    print("  D1で見つからなくてもLLで見つかることがあり、D1とLLの数値は別々に見ます。")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"使い方: {Path(sys.argv[0]).name} cachegrind.out...", file=sys.stderr)
        return 2

    print("=== キャッシュ解析結果 (Cachegrindによるシミュレーション) ===")
    results: dict[str, tuple[float, float]] = {}
    try:
        for filename in sys.argv[1:]:
            path = Path(filename)
            rates = report(path)
            if path.name.endswith(".row"):
                results["row"] = rates
            elif path.name.endswith(".column"):
                results["column"] = rates
        explain_comparison(results)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
