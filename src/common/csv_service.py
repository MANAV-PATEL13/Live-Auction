import csv
import io
from typing import Any


class CSVService:

    @staticmethod
    def read(
        file_content : bytes,
    ) -> tuple[list[str],list[dict[str,Any]]]:

        try:
            content = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError(
                "CSV file must be UTF-8 encoded"
            )

        reader = csv.DictReader(
            io.StringIO(content)
        )

        if not reader.fieldnames:
            raise ValueError(
                "CSV file is empty or has no header"
            )

        columns = [
            column.strip()
            for column in reader.fieldnames
            if column
        ]

        rows = []

        for raw_row in reader:
            row = {}

            for column in columns:
                value = raw_row.get(column)

                if value is not None:
                    value = value.strip()

                row[column] = value or None

            rows.append(row)

        return columns, rows


    @staticmethod
    def validate_columns(
        columns : list[str],
        required_columns : set[str],
    ) -> None:

        available_columns = set(columns)

        missing_columns = (
            required_columns-available_columns
        )

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )


    @staticmethod
    def generate(
        rows: list[dict[str,Any]],
        columns : list[str],
    ) -> bytes:

        output = io.StringIO(
            newline=""
        )

        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            extrasaction="ignore"
        )

        writer.writerheader()
        writer.writerows(rows)

        return output.getvalue().encode(
            "utf-8-sig"
        )