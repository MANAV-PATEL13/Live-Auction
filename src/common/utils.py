from src.common.response import ResponseModel


def success_response(
        data = None,
        message = "Success",
        code = 200
):

    return ResponseModel(
        success=True,
        code=code,
        message=message,
        data=data
    )


def error_response(
        message,
        code = 400,
        errors = None
):

    return ResponseModel(
        success=False,
        code=code,
        message=message,
        errors=errors
    )