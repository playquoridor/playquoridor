export function movePawnEvent(event){
    // Get square
    const targetSquare = event.currentTarget;
    const pawn = document.getElementById(event.detail['player_color'] + '-' + 'pawn');
    pawn.square = targetSquare;
    targetSquare.appendChild(pawn)
}

export function movePawnSoundEvent(event){
    // Get square
    const sound = new Audio(window.sound_dir + '/move_pawn.mp3');
    sound.play();
}

export function removeValidPawnMovesEvent(event){
    // Erase previous valid pawn moves
    const prevValidPawnMoves = document.querySelectorAll('div.valid-pawn-move');
    for (const pawnMove of prevValidPawnMoves){
        pawnMove.remove();
    }
}

export function sendPawnMessageEvent(event, playerColor, gameSocket){
    if (!window.myTurn)
        return

    // Get square
    const targetSquare = event.currentTarget;

    // Get pawn
    const pawn = document.getElementById(playerColor + '-pawn');

    // Assumes valid pawn move
    const message = JSON.stringify({
        'action': 'move_pawn',
        'player_color': pawn.color,
        'source_row': pawn.square.row,
        'source_col': pawn.square.col,
        'target_row': targetSquare.row,
        'target_col': targetSquare.col,
    });
    // console.log(message);
    gameSocket.send(message);
}