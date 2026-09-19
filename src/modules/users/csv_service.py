import csv
import io
from typing import Any

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

        return valid_rows, failed_rows


    @classmethod
    def parse_base_price(
        cls,
        file_content: bytes,
    ) -> tuple[
        list[tuple[int, UserBasePriceCSVRow]],
        list[UserImportRowReport],
    ]:

        columns, raw_rows = CSVService.read(
            file_content
        )

        # Normalize column mappings for flexible CSV formats (e.g. Roll No, Base Price, Bid, etc.)
        def normalize_key(k: str) -> str:
            return k.lower().replace(" ", "").replace("_", "").replace("-", "")

        col_map = {}
        for col in columns:
            norm = normalize_key(col)
            if norm in ("rollno", "rollnumber", "roll", "roll_no"):
                col_map["roll_no"] = col
            elif norm in ("baseprice", "bidprice", "price", "bid", "startingbid", "base_price", "baseprice(m)"):
                col_map["base_price"] = col

        valid_rows = []
        failed_rows = []

        if "roll_no" not in col_map or "base_price" not in col_map:
            # Fallback to standard validation if mapping fails
            try:
                CSVService.validate_columns(
                    columns,
                    cls.BASE_PRICE_REQUIRED_COLUMNS,
                )
            except Exception as exc:
                failed_rows.append(
                    UserImportRowReport(
                        row=1,
                        status="failed",
                        reason=f"Header validation failed: {str(exc)}. Expected columns: roll_no, base_price",
                    )
                )
                return valid_rows, failed_rows

        roll_col = col_map.get("roll_no", "roll_no")
        price_col = col_map.get("base_price", "base_price")

        for row_number, row_data in enumerate(
            raw_rows,
            start=2,
        ):
            raw_roll = row_data.get(roll_col)
            raw_price = row_data.get(price_col)

            if raw_roll is None or raw_price is None:
                failed_rows.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason=f"Missing required values for row {row_number}",
                    )
                )
                continue

            try:
                # Clean up price string (remove 'M', '₹', commas)
                cleaned_price_str = str(raw_price).replace("M", "").replace("m", "").replace(",", "").replace("₹", "").strip()
                parsed_price = int(float(cleaned_price_str))

                row = UserBasePriceCSVRow(
                    roll_no=str(raw_roll).strip(),
                    base_price=parsed_price,
                )

                valid_rows.append(
                    (row_number, row)
                )

            except Exception as exc:
                failed_rows.append(
                    UserImportRowReport(
                        row=row_number,
                        status="failed",
                        reason=f"Invalid row format: {str(exc)}",
                    )
                )

        return valid_rows, failed_rows