class AppException(Exception):

    def __init__(
            self,
            message : str,
            code : int = 400
        ):

            self.message = message
            self.code = code

            super().__init__(message)

class EmailAreadyExistsException(AppException):

      def __init__(self):
            super().__init__(
                  message="Email already exists",
                  code=409
            )

class InvalidCredentialsException(AppException):

     def __init__(self):
          super().__init__(
                message = "Invalid email or password",
                code = "401"
            )

class InvalidEmailCredentialsException(AppException):

    def __init__(self):
        super().__init__(
            message="Invalid email or not found",
            code=401,
        )

class InvalidPasswordCredentialsException(AppException):

    def __init__(self):
        super().__init__(
            message="Invalid password",
            code=401,
        )


class InactiveUserException(AppException):

    def __init__(self):
        super().__init__(
            message="User not found",
            code=404,
        )


class UserNotAllowedException(AppException):

    def __init__(self):
        super().__init__(
            message="User is not allowed to login",
            code=403,
        )