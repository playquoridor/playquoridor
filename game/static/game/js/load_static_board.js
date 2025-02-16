function wallClickCallback(wall, nextCenter, nextWall){
    wall.hasFence = true;
    nextCenter.hasFence = true;
    nextWall.hasFence = true;
}

function changeFenceColorCallback(color) {
    return function (wall, nextCenter, nextWall) {
        wall.style.backgroundColor = color;
        nextCenter.style.backgroundColor = color;
        nextWall.style.backgroundColor = color;
    }
}

function wallEvent(next, callbacks, gameId) {
    return function (event) {
        const board = event.currentTarget.board

        // Get coordinates of next wall
        const row = event.currentTarget.row
        const col = event.currentTarget.col
        const wallType = event.currentTarget.wallType

        // Get wall
        const wallId = wallType + '-' + row + '-' + col
        const wall = board.querySelector('[wall-id=' + wallId + '-' + gameId + ']')
        if (wall.hasFence) {  // Do nothing
            return
        }

        // Proceed with logic
        let nextCenterCol = col;
        let nextCenterRow = row;
        let nextRow = row;
        let nextCol = col;
        if (wallType === 'h') {
            if (nextCol === 0) {
                nextCol = col + 1
            } else if (nextCol === 8) {  // MAX_COL - 1
                nextCol = col - 1
                nextCenterCol = col - 1
            } else if (next) {
                nextCol = col + 1
            } else {
                nextCol = col - 1
                nextCenterCol = col - 1
            }
        } else {  // wall type is 'v'
            if (nextRow === 0) {
                nextRow = row + 1
            } else if (nextRow === 8) {  // MAX_ROW - 1
                nextRow = row - 1
                nextCenterRow = row - 1
            } else if (next) {
                nextRow = row + 1
            } else {  // Putting wall above
                nextRow = row - 1
                nextCenterRow = row - 1
            }
        }

        // Change color of next wall
        const cond = nextCol >= 0 && nextCol < 9 && nextRow >= 0 && nextRow < 9;
        if (cond) {
            // Change color of next center
            const centerId = 'c-' + nextCenterRow + '-' + nextCenterCol
            const nextCenter = board.querySelector('[wall-id=' + centerId + '-' + gameId + ']')

            // Change color of next wall
            const nextWallId = wallType + '-' + nextRow + '-' + nextCol
            const nextWall = board.querySelector('[wall-id=' + nextWallId + '-' + gameId + ']')

            // TODO: Check with server that this is a valid move and execute fence move
            if (!nextWall.hasFence && !nextCenter.hasFence) {
                // Execute transactions in callbacks
                for (let k in callbacks) {
                    callbacks[k](wall, nextCenter, nextWall)
                }
            }
        }
    }
}

function movePawnEvent(event){
    // Get square
    const targetSquare = event.currentTarget;
    const pawn = document.getElementById(event.detail['player_color'] + '-pawn-' + event.detail['game_id']);

    // Remove pawn from source square
    const sourceSquare = pawn.square;  //board.querySelector('[square-id=' + pawn.square.id + ']');
    sourceSquare.innerHTML = ''; //.removeChild(pawn);

    // console.log('Child removed', sourceSquare);
    pawn.square = targetSquare;
    targetSquare.appendChild(pawn);
}

function setWallNumber(data, gameId){
    const wallNumber = document.getElementById('walls_' + data['player'] + '-' + gameId);
    wallNumber.textContent = data['remaining_fences'] + ' walls';
}

function setWinner(data, gameId) {
    const activeGameContainer = document.getElementById('active-game-container');
    if (activeGameContainer) {  // If displaying active game and it's now over
        activeGameContainer.remove();
    } else {
        // Assumes game has ended
        if (data['draw'] !== undefined && data['draw']){  // Game ended in a draw
            const turns = document.querySelectorAll(`[id^="turn_"][id$="${gameId}"]`);
            for (const turn of turns)
                turn.textContent = '🤝'; // '⚖️';
        }else{
            const turn = document.getElementById('turn_' + data['winner_username'] + '-' + gameId);
            turn.textContent = '🏆';
        }
    }

    // Show rating diffs
    if (data['player_username'] + '_delta_rating' in data) {
        console.log('Entering rating diff', data['player_username'])
        const playerRatingDiff = document.getElementById(data['player_username'] + '_delta_rating-' + gameId);
        let delta = data[data['player_username'] + '_delta_rating'];
        if (parseInt(delta) >= 0) {
            delta = '+' + delta;
            playerRatingDiff.classList.add('positive-delta');
        } else {
            playerRatingDiff.classList.add('negative-delta');
        }
        playerRatingDiff.innerText = delta;
    }
    if (data['opponent_username'] + '_delta_rating' in data) {
        const opponentRatingDiff = document.getElementById(data['opponent_username'] + '_delta_rating-' + gameId);
        let delta = data[data['opponent_username'] + '_delta_rating'];
        if (parseInt(delta) >= 0) {
            delta = '+' + delta;
            opponentRatingDiff.classList.add('positive-delta');
        } else {
            opponentRatingDiff.classList.add('negative-delta');
        }
        opponentRatingDiff.innerText = delta;
    }
}

function setActivePlayer(data, gameId){
    const playerBoxes = document.querySelectorAll('[id^="bar"][id$="'+gameId+'"]');  // id^=gameId
    for (const box of playerBoxes){
        box.classList.remove('active-bar');
    }
    const gameEnded = (data['winner_username'] !== undefined && data['winner_username'] !== '') || (data['draw'] !== undefined && data['draw'])
    if (gameEnded){
        setWinner(data, gameId);
        return null;
    }else{
        console.log('Active user', data['active_username']);
        const playerBar = document.getElementById('bar-' + data['active_username'] + '-' + gameId);
        playerBar.classList.add('active-bar');
        return data['active_username'];
    }
}

function placeWallsByStr(board, fenceStr, wallType, gameId){
    const walls = fenceStr.trim().match(/.{1,2}/g);
    if (walls != null)
        for (const wall of walls){
            const row = String(parseInt(wall[1]) - 1);
            const col = String(wall.charCodeAt(0) - 65);
            const subwallId = wallType + '-' + row + '-' + col + '-true-' +gameId;
            const subwall = board.querySelector('[subwall-id=' + subwallId + ']');
            const receiveInitialFenceEvent = new Event('receiveInitialFenceEvent');
            subwall.dispatchEvent(receiveInitialFenceEvent);
        }
}

function placePawnByStr(board, pawnStr, pawnColor, gameId){
    const row = String(parseInt(pawnStr[1]) - 1);
    const col = String(pawnStr.charCodeAt(0) - 65);

    const targetSquareId = 's' + '-' + row + '-' + col + '-' + gameId;
    const targetSquare = board.querySelector('[square-id=' + targetSquareId + ']');

    var pawn = document.getElementById(pawnColor + '-pawn-' + gameId);
    if (pawn) {  // If the pawn exists, we remove it and create it again (should be updated state)
        pawn.remove();
    }

    pawn = document.createElement('div');
    pawn.classList.add('pawn');
    pawn.classList.add(pawnColor + '-pawn');
    pawn.id = pawnColor + '-pawn-' + gameId;
    pawn.color = pawnColor;
    pawn.square = targetSquare;
    targetSquare.appendChild(pawn);

    const winning = (pawnColor === 'white') & (row === '8') | (pawnColor === 'black') & (row === '0');
    return winning;
}

function placePawnsByStr(board, pawnStr, gameId){
    const pawns = pawnStr.trim().match(/.{1,2}/g);
    const whiteWins = placePawnByStr(board, pawns[0], 'white', gameId);
    const blackWins = placePawnByStr(board, pawns[1], 'black', gameId);
    let winningColor = '';
    if (whiteWins)
        winningColor = 'white';
    else if (blackWins)
        winningColor='black';
    return winningColor;
}

function setupBoardFromFEN(FEN, gameId, playerColor, playerUsername, opponentUsername){
    const board = document.getElementById('board-'+gameId);
    const FEN_split = FEN.split('/');

    // Horizontal fences
    const hWalls = FEN_split[0];
    placeWallsByStr(board, hWalls, 'h', gameId);

    // Vertical fences
    const vWalls = FEN_split[1];
    placeWallsByStr(board, vWalls, 'v', gameId);

    // Place pawns
    placePawnsByStr(board, FEN_split[2], gameId);

    // Number of walls available
    // In case of spectator, playerUsername is white and opponentUsername is black
    const wallNumbers = FEN_split[3].trim().split(' ');
    const isSpectator = playerColor === null;
    const whitePlayer = playerColor === 'white' || isSpectator? playerUsername : opponentUsername;
    const blackPlayer = playerColor === 'black' ? playerUsername : opponentUsername;
    setWallNumber({'player': whitePlayer, 'remaining_fences': wallNumbers[0]}, gameId);
    setWallNumber({'player': blackPlayer, 'remaining_fences': wallNumbers[1]}, gameId);

    // Set active player
    const activePlayer = FEN_split[4].trim() === '1' ? whitePlayer : blackPlayer;
    let winnerUsername = '';
    let draw = false;
    if (FEN_split.length > 6) {
        let winnerColor = FEN_split[6].trim().length > 0 ? parseInt(FEN_split[6]) : null;
        if (winnerColor === 0)
            winnerUsername = whitePlayer;
        else if (winnerColor === 1)
            winnerUsername = blackPlayer;
        else if (winnerColor === -1){
            draw = true;
            winnerUsername = ''
        }
    }

    setActivePlayer({'active_username': activePlayer, 'winner_username': winnerUsername, 'draw': draw}, gameId);
}

/*
Initialise board and walls
*/
function createSubWall(board, row, col, wallType, next, gameId){
    const subwall = document.createElement('div');
    if (wallType === 'v')
        subwall.classList.add('subvwall');
    else
        subwall.classList.add('subhwall');
    subwall.row = row
    subwall.col = col
    subwall.board = board
    subwall.wallType = wallType
    subwall.next = next
    subwall.setAttribute('subwall-id', wallType + '-' + row + '-' + col + '-' + next + '-' + gameId);

    // Custom event. Places a fence on the board when receiving the asynchronous fence message
    subwall.addEventListener('receiveFenceEvent', (event) => {
      wallEvent(next,[changeFenceColorCallback('\#664229'), wallClickCallback], gameId)(event);
    });

    // Custom event. Places a fence on the board when receiving the asynchronous fence message
    subwall.addEventListener('receiveInitialFenceEvent', (event) => {
      wallEvent(next,[changeFenceColorCallback('\#664229'), wallClickCallback], gameId)(event);
    });
    return subwall
}

function createWall(board, row, col, wallType, gameId){
    // Create a new horizontal wall element
    const wall = document.createElement('div');
    if (wallType === 'v')
        wall.classList.add('vertical-wall');
    else
        wall.classList.add('horizontal-wall');
    wall.row = row
    wall.col = col
    wall.board = board
    wall.wallType = wallType
    wall.setAttribute('wall-id', wall.wallType + '-' + row + '-' + col + '-' + gameId);

    const next = wallType === 'v';
    const subwall1 = createSubWall(board, row, col, wallType, next, gameId);
    wall.appendChild(subwall1);

    const subwall2 = createSubWall(board, row, col, wallType, !next, gameId);
    wall.appendChild(subwall2);

    return wall
}

function createSquare(board, i, j, playerColor, gameId){
    // Create a new square element
    const square = document.createElement('div');
    square.classList.add('square');
    square.row = i;
    square.col = j;
    square.board = board;
    square.id = 's-' + i + '-' + j + '-' + gameId;
    square.setAttribute('row', i);
    square.setAttribute('col', j);
    square.setAttribute('square-id', 's-' + i + '-' + j + '-' + gameId);

    square.addEventListener('movePawnEvent', (event) => {
        movePawnEvent(event);
    });

    return square
}

function createBoard(gameId, playerColor){
    /*
    Player information
    */
    //const gameId = JSON.parse(document.getElementById('game-id').textContent)
    // const playerColor = JSON.parse(document.getElementById('player-color').textContent);
    // const FEN =  JSON.parse(document.getElementById('FEN').textContent);

    /*
    Setup board
     */

    // Get a reference to the quoridor-board element
    const board = document.getElementById('board-'+gameId);

    // Use a for loop to add the squares to the board
    for (let i = 8; i >= 0; i--) {
        for (let j = 0; j < 9; j++) {
            // Create a new square element
            const square = createSquare(board, i, j, playerColor, gameId);

            // Append the square to the quoridor-board element
            board.appendChild(square);

            // Add vertical fence gaps
            if (j < 8) {  // Last column
                // Create a new horizontal wall element
                const vwall = createWall(board, i, j, 'v', gameId);

                //vwall.addEventListener('mouseover', wallClickListener(true));
                //vwall.addEventListener('mouseleave', wallClickListener(false));

                // Append the square to the quoridor-board element
                board.appendChild(vwall);
            }
        }
        if (i > 0){
            for (let j = 0; j < 17; j++) {
                const iWall = i - 1;

                // Add horizontal fence gaps
                if (j % 2 === 0){  // horizontal wall
                    // Create a new horizontal wall element
                    const jWall = j / 2;
                    const hwall = createWall(board, iWall, jWall, 'h', gameId)

                    // Append the square to the quoridor-board element
                    board.appendChild(hwall);
                }else{  // center
                    // Create a new center wall element
                    const wallCenter = document.createElement('div');
                    wallCenter.classList.add('wall-center');

                    const jWall = (j + 1) / 2 - 1;
                    wallCenter.setAttribute('wall-id', 'c-' + iWall + '-' + jWall + '-' + gameId);

                    // Append the square to the quoridor-board element
                    board.appendChild(wallCenter);
                }
            }
        }
    }
}

// Define the function as a global variable
var FEN = document.currentScript.dataset.fen;
var gameId = document.currentScript.dataset.gameid;  // JSON.parse(document.getElementById('game-id').textContent)
var playerColor = document.currentScript.dataset.playercolor;  // JSON.parse(document.getElementById('player-color').textContent);
var playerUsername = document.currentScript.dataset.playerusername; // JSON.parse(document.getElementById('player').textContent);
var opponentUsername = document.currentScript.dataset.opponentusername; // JSON.parse(document.getElementById('opponent').textContent);
var gameEnded = document.currentScript.dataset.gameended === 'True';
var board = document.getElementById('board-' + gameId);
var showLive =  !document.currentScript.dataset.showlive;

createBoard(gameId, playerColor);
setupBoardFromFEN(FEN, gameId, playerColor, playerUsername, opponentUsername);

// Show live game
if (!gameEnded && showLive){
    // Game hasn't ended, connect to socket
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const gameSocket = new WebSocket(
        ws_scheme
        +'://'
        + window.location.host
        + '/ws/game/'
        + gameId
        + '/'
    )

    gameSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const board = document.getElementById('board-' + data['game_id']);
        switch (data['action']){
            case 'FEN':
                console.log('Setting up FEN from consumer...', playerColor);
                //setupBoardFromFEN(data['FEN'], data['game_id'], playerColor, playerUsername, opponentUsername);
                setupBoardFromFEN(data['FEN'], data['game_id'], data['player_color'], data['player_username'], data['opponent_username']);
                break;
            case 'place_fence':
                // TODO: Assert integrity of received data, i.e. subwallId matches center coords
                const subwallId = data['wall_type'] + '-' +
                    data['row'] + '-' + data['col'] + '-true-' + data['game_id'];
                const subwall = board.querySelector('[subwall-id=' + subwallId + ']');
                const receiveFenceEvent = new Event('receiveFenceEvent');
                subwall.dispatchEvent(receiveFenceEvent);
                setWallNumber(data, data['game_id']);
                setActivePlayer(data, data['game_id']);
                break;
            case 'move_pawn':
                // const sourceSquareId = 's' + '-' + data['source_row'] + '-' + data['source_col'];
                const targetSquareId = 's' + '-' + data['target_row'] + '-' + data['target_col'] + '-' + data['game_id'];
                const targetSquare = board.querySelector('[square-id=' + targetSquareId + ']');
                const movePawnEvent = new CustomEvent('movePawnEvent', {'detail': data});
                targetSquare.dispatchEvent(movePawnEvent);
                setActivePlayer(data, data['game_id']);
                break;
            case 'game_over':
                setActivePlayer(data, data['game_id']);
                // setWinner(data, data['game_id']);
                // gameSocket.close();
                break;
        }
    };

    gameSocket.onopen = function (e){
        // requestBoardState(gameSocket, playerColor);
        const boardStateRequest = JSON.stringify({
            'action': 'request_board_state',
            'player_color': playerColor
        });
        gameSocket.send(boardStateRequest);
    }

    gameSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

}