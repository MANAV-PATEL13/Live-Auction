import csv
import io

from pydantic import ValidationError
from src.common.csv_service import CSVService

from src.modules.users.csv_schema import UserCSVRow, UserImportRowReport, UserBasePriceCSVRow

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

    BASE_PRICE_REQUIRED_COLUMNS = {
        "roll_no",
        "base_price",
    }

    @classmethod
    def parse(
        cls,
        file_content : bytes,
    ) -> tuple[
            list[tuple[int,UserCSVRow]],
            list[UserImportRowReport]
        ]:

        columns, rows = CSVService.read(
            file_content
        )

        CSVService.validate_columns(
            columns,
            cls.REQUIRED_COLUMNS,
        )

        valid_rows = []
        failed_rows = []

        for row_number, row_data in enumerate(
            rows,
            start=2,
        ):

            user_data = {
                column : row_data.get(column)
                for column in cls.ALL_COLUMNS
            }

            try:
                row = UserCSVRow(
                    **user_data
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

            return valid_rows, 


    @classmethod
    def parse_base_price(
        cls,
        file_content: bytes,
    ) -> tuple[
        list[tuple[int, UserBasePriceCSVRow]],
        list[UserImportRowReport],
    ]:

        columns, rows = CSVService.read(
            file_content
        )

        CSVService.validate_columns(
            columns,
            cls.BASE_PRICE_REQUIRED_COLUMNS,
        )

        valid_rows = []
        failed_rows = []

        for row_number, row_data in enumerate(
            rows,
            start=2,
        ):
            try:
                row = UserBasePriceCSVRow(
                    roll_no=row_data.get("roll_no"),
                    base_price=row_data.get("base_price"),
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
                        reason="; ".join(messages),
                    )
                )

        return valid_rows, failed_rows