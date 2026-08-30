class AppException(Exception):

    def __init__(
            self,
            message : str,
            code : int  
        ):

            self.message = message
            self.code = code

            super().__init__(message)

class InvalidTokenException(AppException):

    def __init__(self):
        super().__init__(
            message="Invalid or expired token",
            code=401,
        )

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
                code = 401
            )


class InactiveUserException(AppException):

    def __init__(self):
        super().__init__(
            message="User not found",
            code=403,
        )


class UserNotAllowedException(AppException):

    def __init__(self):
        super().__init__(
            message="User is not allowed to login",
            code=403,
        )


class ForbiddenException(AppException):

     def __init__(self, message : str = "You do not have permission to perform this action"):
          super().__init__(
               message=message,
               code=403
          )

class NotFoundException(AppException):

     def __init__(self, message : str = "Resource not found"):
          super().__init__(
               message = message,
               code = 404
            )

          
class ConflictException(AppException):

     def __init__(self, message : str = "Resource already exists"):
          super().__init__(
               message = message,
               code = 409
            )
          