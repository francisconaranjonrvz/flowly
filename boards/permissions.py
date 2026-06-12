# Permisos personalizados para tableros.

from .models import BoardMembership


def user_can_access_board(user, board):
    """Comprueba si el usuario es dueño o miembro del tablero."""
    if not user or not user.is_authenticated:
        return False
    if board.owner_id == user.id:
        return True
    return BoardMembership.objects.filter(board=board, user=user).exists()
