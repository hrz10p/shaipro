import argparse
import glob
import os
from typing import List


def list_files(input_dir: str, pattern: str) -> List[str]:
    search_pattern = os.path.join(input_dir, pattern)
    files = sorted(glob.glob(search_pattern))
    return [f for f in files if os.path.isfile(f)]


def concatenate_csv_files(input_files: List[str], output_file: str) -> None:
    if not input_files:
        open(output_file, "w").close()
        return

    header_written = False
    expected_header = None

    with open(output_file, "w", encoding="utf-8") as out_fp:
        for idx, file_path in enumerate(input_files):
            with open(file_path, "r", encoding="utf-8") as in_fp:
                first_line = in_fp.readline()
                if not header_written:
                    expected_header = first_line
                    out_fp.write(first_line)
                    header_written = True
                else:
                    if first_line != expected_header:
                        out_fp.write(first_line)

                for line in in_fp:
                    out_fp.write(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concatenate transaction and transfer CSV files.")
    parser.add_argument(
        "--input-dir",
        default="/data/raw",
        help="Directory containing the raw CSV files (default: /data/raw)",
    )
    parser.add_argument(
        "--transactions-pattern",
        default="*_transactions_*.csv",
        help="Glob pattern for transaction files (default: *_transactions_*.csv)",
    )
    parser.add_argument(
        "--transfers-pattern",
        default="*_transfers_*.csv",
        help="Glob pattern for transfer files (default: *_transfers_*.csv)",
    )
    parser.add_argument(
        "--out-transactions",
        default="transactions_all.csv",
        help="Output CSV filename for concatenated transactions (default: transactions_all.csv)",
    )
    parser.add_argument(
        "--out-transfers",
        default="transfers_all.csv",
        help="Output CSV filename for concatenated transfers (default: transfers_all.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory to write outputs to (default: same as --input-dir)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir or input_dir)
    os.makedirs(output_dir, exist_ok=True)

    transaction_files = list_files(input_dir, args.transactions_pattern)
    transfer_files = list_files(input_dir, args.transfers_pattern)

    out_transactions_path = os.path.join(output_dir, args.out_transactions)
    out_transfers_path = os.path.join(output_dir, args.out_transfers)

    concatenate_csv_files(transaction_files, out_transactions_path)
    concatenate_csv_files(transfer_files, out_transfers_path)

    print(f"Wrote {out_transactions_path} from {len(transaction_files)} files")
    print(f"Wrote {out_transfers_path} from {len(transfer_files)} files")


if __name__ == "__main__":
    main()


