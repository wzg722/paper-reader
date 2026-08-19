from rest_framework.response import Response


def ok(data=None, message='ok', status=200):
    return Response({'code': 0, 'message': message, 'data': data}, status=status)


def fail(message='error', code=1, status=400, data=None):
    return Response({'code': code, 'message': message, 'data': data}, status=status)
