import csv
import io

from pydantic import ValidationError

from src.modules.users.csv_schema import UserCSVRow, UserImportRowReport

class UserCSVService:

    REQUIRED_COLUMNS = {
        "first_name",
        "last_name",
        "roll_no",
        "email",
    }

    ALL_COLUMNS = {
        "first_name",
        "middle_name",
        "last_name",
        "roll_no",
        "email",
        "mobile",
        "image_url"
    }

    @classmethod
    def parse(
        cls,
        file_content : bytes,
    ) -> tuple[list[tuple[int,UserCSVRow]],list[UserImportRowReport]]:

        valid_rows : list[tuple[int,UserCSVRow]] = []
        failed_rows : list[UserImportRowReport] = []

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

        columns = {
            column.strip()
            for column in reader.fieldnames
            if column
        }

        missing_columns = (
            cls.REQUIRED_COLUMNS - columns
        )

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        for row_number, raw_row in enumerate(
            reader,
            start=2
        ):

            # normalize column values
            row_data = {}

            for column in cls.ALL_COLUMNS:
                value = raw_row.get(column)

                if value is not None:
                    value = value.strip()

                row_data[column] = value or None


            try:
                row = UserCSVRow(
                    **row_data
                )

                valid_rows.append(
                    (row_number, row)
                )

            except ValidationError as exc:

                messages = []

                for error in exc.errors():
                    field = ".".join(
                        str(x)
                        for x in error["loc"]
                    )

                    messages.append(
                        f"{field}: {error['msg']}"
                    )

                failed_rows.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason="; ".join(messages)
                    )
                )

        return valid_rows, failed_rows