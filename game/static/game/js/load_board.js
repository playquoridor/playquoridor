//import {wallClickListener} from './wall_listeners.js';
import {wallClickCallback,
  sendFenceMessageCallback,
  changeFenceColorCallback,
    placeWallSoundCallback,
    changeFencePropertyCallback,
    changeCursorType,
  wallEvent} from './wall_listeners.js';
import {sendPawnMessageEvent,
    movePawnEvent,
    movePawnSoundEvent,
    removeValidPawnMovesEvent,
} from './square_listeners.js';
import {
    squareStr2List
} from './fen_utils.js'

/*
Sounds
 */
function playStartGameSound() {
    const sound = new Audio(window.sound_dir + '/start.wav');
    sound.play();
}

function playGameWinSound() {
    const sound = new Audio(window.sound_dir + '/win.wav');
    sound.play();
}

function playGameLossSound() {
    const sound = new Audio(window.sound_dir + '/loss.wav');
    sound.play();
}

function playGameDrawSound() {
    const sound = new Audio(window.sound_dir + '/draw.wav');
    sound.play();
}

/*
Requests
 */
function requestValidPawnMoves(socket, playerColor){
    const pawnMovesRequest = JSON.stringify({
        'action': 'request_pawn_moves',
        'player_color': playerColor
    });
    socket.send(pawnMovesRequest);
}

function requestBoardState(socket, playerColor){
    const boardStateRequest = JSON.stringify({
        'action': 'request_board_state',
        'player_color': playerColor
    });
    socket.send(boardStateRequest);
}

function requestTimeCheck(socket, playerColor){
    const timeCheckRequest = JSON.stringify({
        'action': 'time_check',
        'player_color': playerColor
    });
    socket.send(timeCheckRequest);
}

/*
Sets
 */
function setWallNumber(data){
    const wallNumber = document.getElementById('walls_' + data['player_color']);
    wallNumber.textContent = data['remaining_fences'] + ' walls';
}

function setWinner(data, pColor, isSpectator, oColor, gameSocket){
    const gameMessage = document.getElementById('game-message');

    // Assumes game has ended
    if (data['abort'] !== undefined && data['abort']) {
        gameMessage.innerText = 'Game aborted';
        if ('just_finished' in data)
            playGameDrawSound();
    }else if (data['draw'] !== undefined && data['draw']){  // Game ended in a draw
        const turns = document.querySelectorAll('[id^="turn_"]');
        for (const turn of turns)
            turn.textContent = '🤝'; // '⚖️';
        gameMessage.innerText = 'Draw';
        if ('just_finished' in data)
            playGameDrawSound();
    }else{
        const winnerColor = data['winner_color'];
        const winnerUsername = data['winner_username'];
        const turn = document.getElementById('turn_' + winnerColor);
        turn.textContent = '🏆';

        gameMessage.innerText = 'Player ' + winnerColor + ' wins';
        if ('just_finished' in data){
            if (pColor == winnerColor)
                playGameWinSound();
            else
                playGameLossSound();
        }
    }

    // Show rematch button
    if (!isSpectator && 'end_time' in data && 'time_now' in data) {  // TODO: Only if game just finished
        const endTime = new Date(data['end_time']);
        const now = new Date(data['time_now']);

        if ((now - endTime)/1000 < 120) {  // If game finished less than 5 minutes ago
            const rematch = document.getElementById('rematch-box');
            rematch.style.display = 'inline-block';
            // TODO: Only show if this in my last game
            
            const rematchButton = document.getElementById('rematch-button');
            rematchButton.onclick = function (event) {
                sendRematchChallenge(gameSocket);
            };
        }
    }

    // Hide draw / resign buttons
    // const abort = document.getElementById('abort-button');
    // abort.style.display = 'none';
    const draw = document.getElementById('draw-button');
    draw.style.display = 'none';
    const resign = document.getElementById('resign-button');
    resign.style.display = 'none';
    const optionsBox = document.getElementById('game-options-box')
    optionsBox.style.display = 'none'

    // Show rating diffs
    if (pColor+'_delta_rating' in data) {
        const playerRatingDiff = document.getElementById(pColor + '_delta_rating');
        let delta = data[pColor + '_delta_rating'];
        if (parseInt(delta) >= 0){
            delta = '+' + delta;
            playerRatingDiff.classList.add('positive-delta');
        }else {
            playerRatingDiff.classList.add('negative-delta');
        }
        playerRatingDiff.innerText = delta;
    }
    if(oColor+'_delta_rating' in data) {
        const opponentRatingDiff = document.getElementById(oColor + '_delta_rating');
        let delta = data[oColor + '_delta_rating'];
        if (parseInt(delta) >= 0){
            delta = '+' + delta;
            opponentRatingDiff.classList.add('positive-delta');
        }else {
            opponentRatingDiff.classList.add('negative-delta');
        }
        opponentRatingDiff.innerText = delta;
    }
}

function setActivePlayer(data, pColor, isSpectator, oColor, gameSocket){
    const playerBoxes = document.querySelectorAll('[id^="bar"]');  // id^=gameId
    for (const box of playerBoxes){
        box.classList.remove('active-bar');
    }
    const gameEnded = (data['winner_color'] !== undefined && data['winner_color'] !== '') || (data['draw'] !== undefined && data['draw'])
    if (gameEnded) {
        setWinner(data, pColor, isSpectator, oColor, gameSocket);
        return null;
    }
    else{
        const playerBar = document.getElementById('bar-' + data['active_color']);
        playerBar.classList.add('active-bar');

        return data['active_color'];
    }
}

function setTime(color, remainingSeconds) {
    const playerTimeBox = document.getElementById('timer-' + color);
    const remainingTime = new Date(remainingSeconds * 1000).toISOString().slice(14, 19);
    playerTimeBox.innerText = remainingTime;
}

/*
Time
 */
let activeInterval;
function startTimer(activeColor, gameSocket) {
    if (activeInterval)
        clearInterval(activeInterval);

    const playerTimeBox = document.getElementById('timer-' + activeColor);
    const splitTime = playerTimeBox.innerText.split(':');
    const minutes = parseInt(splitTime[0]);
    const seconds = parseInt(splitTime[1]);
    var timer = minutes * 60 + seconds;
    activeInterval = setInterval(function (){
        if (--timer <= 0) {
            // Stop timer
            timer = 0;
            clearInterval(activeInterval);

            // Request time check
            requestTimeCheck(gameSocket, activeColor);
        }
        playerTimeBox.textContent = new Date(timer * 1000).toISOString().slice(14, 19);
    }, 1000);

}

/*
Place
 */
function placeWallsByStr(fenceStr, wallType, gameId){
    const board = document.getElementById('board-'+gameId);
    const walls = fenceStr.trim().match(/.{1,2}/g);
    if (walls != null)
        for (const wall of walls){
            const row = String(parseInt(wall[1]) - 1);
            const col = String(wall.charCodeAt(0) - 65);
            const subwallId = wallType + '-' + row + '-' + col + '-' + 'true';
            const subwall = board.querySelector('[subwall-id=' + subwallId + ']');
            const receiveInitialFenceEvent = new Event('receiveInitialFenceEvent');
            subwall.dispatchEvent(receiveInitialFenceEvent);
        }
}

function placePawnByStr(pawnStr, pawnColor, gameId){
    const board = document.getElementById('board-'+gameId);
    const row = String(parseInt(pawnStr[1]) - 1);
    const col = String(pawnStr.charCodeAt(0) - 65);

    const targetSquareId = 's' + '-' + row + '-' + col;
    const targetSquare = board.querySelector('[square-id=' + targetSquareId + ']');

    var pawn = document.getElementById(pawnColor + '-pawn'); // '-' + gameId
    if (pawn) {  // If the pawn exists, we remove it and create it again (should be updated state)
        pawn.remove();
    }

    pawn = document.createElement('div');
    pawn.classList.add('pawn');
    pawn.classList.add(pawnColor + '-pawn');
    pawn.id = pawnColor + '-pawn';  // '-' + gameId
    pawn.color = pawnColor;
    pawn.square = targetSquare;
    targetSquare.appendChild(pawn);

    const winning = (pawnColor === 'white') & (row === '8') | (pawnColor === 'black') & (row === '0');
    return winning;
}

function placePawnsByStr(pawnStr, gameId){
    const pawns = pawnStr.trim().match(/.{1,2}/g);
    const whiteWins = placePawnByStr(pawns[0], 'white', gameId);
    const blackWins = placePawnByStr(pawns[1], 'black', gameId);
    let winningColor = -1;
    if (whiteWins)
        winningColor = 0;
    else if (blackWins)
        winningColor = 1;
    return winningColor;
}

/*
Initialise board and walls
*/
function createSubWall(board, row, col, wallType, next, playerColor, isSpectator, gameSocket){
    const subwall = document.createElement('div');
    if (wallType === 'v')
        subwall.classList.add('subvwall');
    else
        subwall.classList.add('subhwall');
    // if (!isSpectator)
    // subwall.classList.add('pointer');
    subwall.row = row
    subwall.col = col
    subwall.board = board
    subwall.wallType = wallType
    subwall.next = next
    subwall.setAttribute('subwall-id', wallType + '-' + row + '-' + col + '-' + next);

    // S1
    if (!isSpectator) {
        subwall.addEventListener('click',
            wallEvent(next, [sendFenceMessageCallback(gameSocket, playerColor)]));  // changeFenceColorCallback('\#664229'), wallClickCallback,
        subwall.addEventListener('mouseover',
            wallEvent(next, [changeFenceColorCallback(true, '\#664229'), changeCursorType(true, 'pointer')]));
        subwall.addEventListener('mouseleave',
            wallEvent(next, [changeFenceColorCallback(false, '\#e5d3b3'), changeCursorType(false, 'auto')]));
    }

    // Custom event. Places a fence on the board when receiving the asynchronous fence message
    subwall.addEventListener('receiveFenceEvent', (event) => {
      removeValidPawnMovesEvent(event);
      wallEvent(next,
          [placeWallSoundCallback(), changeFenceColorCallback(false,'\#664229'), changeCursorType(false, 'auto'), wallClickCallback],
          false)(event);
      requestValidPawnMoves(gameSocket, playerColor);
    });

    // Custom event. Places a fence on the board when receiving the asynchronous fence message
    subwall.addEventListener('receiveInitialFenceEvent', (event) => {
      wallEvent(next,
          [changeFenceColorCallback(false,'\#664229'), wallClickCallback],
          false)(event);
    });
    subwall.addEventListener('highlightFenceEvent', (event) => {
      wallEvent(next,
          [changeFencePropertyCallback('highlighted')],
          false)(event);
    });
    return subwall
}

function createWall(board, row, col, wallType, playerColor, isSpectator, gameSocket){
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
    wall.setAttribute('wall-id', wall.wallType + '-' + row + '-' + col);

    const next = wallType === 'v';
    const subwall1 = createSubWall(board, row, col, wallType, next, playerColor, isSpectator, gameSocket)
    wall.appendChild(subwall1);

    const subwall2 = createSubWall(board, row, col, wallType, !next, playerColor, isSpectator, gameSocket)
    wall.appendChild(subwall2);

    return wall
}

function createSquare(board, i, j, playerColor, isSpectator, gameSocket, update=false){
    const squareId = 's-' + i + '-' + j;

    // Create a new square element
    if (update) {
        const square = document.getElementById(squareId);
        // TODO: In case of socket reconnection?
        // square.removeEventListener('click');
        // square.removeEventListener('movePawnEvent');
    }
    const square = document.createElement('div');
    square.classList.add('square');
    square.row = i;
    square.col = j;
    square.board = board;
    square.id = squareId;
    square.setAttribute('row', i);
    square.setAttribute('col', j);
    square.setAttribute('square-id', 's-' + i + '-' + j);

    // Event listeners
    if (!isSpectator)
        square.addEventListener('click', (event) => sendPawnMessageEvent(event, playerColor, gameSocket))  // [removeValidPawnMovesCallback, squareClickCallback, sendPawnMessageCallback(gameSocket)]
    square.addEventListener('movePawnEvent', (event) => {
        removeValidPawnMovesEvent(event);
        movePawnEvent(event);
        movePawnSoundEvent();
        requestValidPawnMoves(gameSocket, playerColor);
    });

    return square
}

function createBoard(gameId, playerColor, isSpectator, gameSocket){
    // Get a reference to the quoridor-board element
    const board = document.getElementById('board-'+gameId);

    // Use a for loop to add the squares to the board
    for (let i = 8; i >= 0; i--) {
        for (let j = 0; j < 9; j++) {
            // Create a new square element
            const square = createSquare(board, i, j, playerColor, isSpectator, gameSocket);

            // Append the square to the quoridor-board element
            board.appendChild(square);

            // Add vertical fence gaps
            if (j < 8) {  // Last column
                // Create a new horizontal wall element
                const vwall = createWall(board, i, j, 'v', playerColor, isSpectator, gameSocket);

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
                    const hwall = createWall(board, iWall, jWall, 'h', playerColor, isSpectator, gameSocket)

                    // Append the square to the quoridor-board element
                    board.appendChild(hwall);
                }else{  // center
                    // Create a new center wall element
                    const wallCenter = document.createElement('div');
                    wallCenter.classList.add('wall-center');

                    const jWall = (j + 1) / 2 - 1;
                    wallCenter.setAttribute('wall-id', 'c-' + iWall + '-' + jWall);

                    // Append the square to the quoridor-board element
                    board.appendChild(wallCenter);
                }
            }
        }
    }
}

function setupBoardFromFEN(FEN, gameId, playerColor, pColor, isSpectator, oColor, gameSocket){
    const FEN_split = FEN.split('/');

    // Horizontal fences
    const hWalls = FEN_split[0];
    placeWallsByStr(hWalls, 'h', gameId);

    // Vertical fences
    const vWalls = FEN_split[1];
    placeWallsByStr(vWalls, 'v', gameId);

    // Place pawns
    placePawnsByStr(FEN_split[2], gameId);

    // Number of walls available
    const wallNumbers = FEN_split[3].trim().split(' ');
    setWallNumber({'player_color': 'white', 'remaining_fences': wallNumbers[0]});
    setWallNumber({'player_color': 'black', 'remaining_fences': wallNumbers[1]});

    // Set active player and set winner if provided
    // let winnerUsername = '';
    let wcolor = ''
    let draw = false;
    let abort = false;
    const activeColor = FEN_split[4].trim() === '1' ? 'white' : 'black';
    if (FEN_split.length > 6) {
        let winnerColor = FEN_split[6].trim().length > 0 ? parseInt(FEN_split[6]) : null;
        if (winnerColor === 0)
            wcolor = 'white';
        else if (winnerColor === 1)
            wcolor = 'black';
        else if (winnerColor === -1)
            draw = true;
        else if (winnerColor === -2)
            abort = true;
    }
    setActivePlayer({'active_color': activeColor, 'winner_color': wcolor, 'draw': draw},
        pColor, isSpectator, oColor, gameSocket);
    window.myTurn = (activeColor === pColor);

    // Set remaining time (requires remaining times)
    if (FEN_split.length > 7) {
        const remainingTimes = FEN_split[7].trim().split(' ');
        setTime('white', parseFloat(remainingTimes[0]));
        setTime('black', parseFloat(remainingTimes[1]));
    }

    // Setup buttons and start timer (requires move count)
    if (FEN_split.length > 5) {
        const moveCount = parseInt(FEN_split[5]);
        if (wcolor === '' && !draw && !abort){
            if (moveCount <= 1) {
                if (moveCount === 0)
                    playStartGameSound();

                // Show abort button
                if (!isSpectator) {
                    const abort = document.getElementById('abort-button');
                    abort.style.display = 'inline-block';
                }

                // Hide game options box
                const gameOptions = document.getElementById('game-options-box');
                gameOptions.style.display = 'none';
            }
            else if(moveCount > 1){
                startTimer(activeColor, gameSocket);

                // Hide abort button
                const abort = document.getElementById('abort-button');
                abort.style.display = 'none';

                // Show game options box
                if (!isSpectator) {
                    const gameOptions = document.getElementById('game-options-box');
                    gameOptions.style.display = 'inline-block';
                }
            }
        }
    }
}

function resetFences() {
    // Get all div elements with an attribute starting with "data-custom-"
    const walls = document.querySelectorAll('div[wall-id]');

    // Loop through the matched elements and do something with them
    walls.forEach(function (div) {
        div.hasFence = false;
        div.style = '';
    });

    // Get all div elements with an attribute starting with "data-custom-"
    const centers = document.querySelectorAll('.center');

    // Loop through the matched elements and do something with them
    centers.forEach(function (div) {
        div.hasFence = false;
        div.style = '';
    });
}

/*
Analysis panel from PGN
*/
function createPartialFENs(moveList, totalMoves, analysisFENs){
    for (let i=1; i <= totalMoves; i++) {
        let splitFEN = analysisFENs[i-1].split('/');
        let horizontalFences = splitFEN[0];
        let verticalFences = splitFEN[1];
        let pawnPositions = splitFEN[2].trim().match(/.{1,2}/g);
        let nFences = splitFEN[3].trim().split(' ');

        const nPlayers = pawnPositions.length;
        const prevTurn = i % nPlayers;
        const turn = (i - 1) % nPlayers;
        let turnStr = String((turn + 1) % nPlayers + 1);
        const _i = Math.floor((i - 1) / 2)
        const move = moveList[_i].trim().split(' ')[turn];

        if (move.length === 3) {
            // Placing fence
            const wallType = move[2];
            const squareStr = move.substring(0, 2);

            // Create new FEN
            if (wallType === 'h') {
                horizontalFences = horizontalFences + squareStr;
            } else {
                verticalFences = verticalFences + squareStr;
            }
            nFences[turn] -= 1;
        } else {
            // Move pawn
            if (move === pawnPositions[turn]){ // Pawn not moving, do not update turn (useful for tutorials)
                turnStr = analysisFENs.slice(-1).at('/').at(-1);
            }
            pawnPositions[turn] = move;
        }

        const newFEN = horizontalFences + '/'
            + verticalFences + '/'
            + pawnPositions.join('') + '/'
            + nFences.join(' ') + '/'
            + turnStr; // String((turn + 1) % nPlayers + 1);
        analysisFENs.push(newFEN);
    }
    return analysisFENs;
}

function scrollParentToChild(parent, child) {
    // Ref: https://stackoverflow.com/questions/45408920/plain-javascript-scrollintoview-inside-div
    // Where is the parent on page
    const parentRect = parent.getBoundingClientRect();
    // What can you see?
    const parentViewableArea = {
        height: parent.clientHeight,
        width: parent.clientWidth
    };

    // Where is the child
    const childRect = child.getBoundingClientRect();
    // Is the child viewable?
    const isViewable = (childRect.top >= parentRect.top) && (childRect.bottom <= parentRect.top + parentViewableArea.height);

    // if you can't see the child try to scroll parent
    if (!isViewable) {
        // Should we scroll using top or bottom? Find the smaller ABS adjustment
        const scrollTop = childRect.top - parentRect.top;
        const scrollBot = childRect.bottom - parentRect.bottom;
        if (Math.abs(scrollTop) < Math.abs(scrollBot)) {
            // we're near the top of the list
            parent.scrollTop += scrollTop;
        } else {
            // we're near the bottom of the list
            parent.scrollTop += scrollBot;
        }
    }

}

function swapSelectedMoveDiv(prevAnalysisMoveNumber, currAnalysisMoveNumber){
    if (prevAnalysisMoveNumber > 0) {
        const prevMovDiv = document.getElementById('move_id-' + String(prevAnalysisMoveNumber - 1));
        prevMovDiv.classList.remove('selected');
    }
    if (currAnalysisMoveNumber > 0) {
        const currMoveDiv = document.getElementById('move_id-' + String(currAnalysisMoveNumber - 1));
        currMoveDiv.classList.add('selected');
        const container = document.getElementById('move-list');
        scrollParentToChild(container, currMoveDiv);
    }
}

function createAnalysisPanel(PGN, gameId, playerColor, pColor, isSpectator, oColor, analysisFENs) {
    const moveList = PGN.split(/\d+\.\s/).filter(move => move.trim());
    const gameAnalysisContainer = document.getElementById('game-analysis-container');
    gameAnalysisContainer.classList.remove('hidden');

    const moveListBox = document.getElementById('move-list');
    moveListBox.innerHTML = ''; // Removes all current content
    let totalMoves = 0;
    for (const [i, move] of moveList.entries()){
        const moveSplit = move.trim().split(' ');
        const moveNumberDiv = document.createElement('div');
        moveNumberDiv.classList.add('move-list-row-number');
        moveNumberDiv.innerText = i + 1;
        moveNumberDiv.id = 'move_number_id-' + String(i);
        moveNumberDiv.onclick = function (event){
            resetFences();
            const newAnalysisMoveNumber = parseInt(event.target.id.split('-')[1])*2 + 1;
            swapSelectedMoveDiv(analysisMoveNumber, newAnalysisMoveNumber);
            analysisMoveNumber = newAnalysisMoveNumber;
            setupBoardFromFEN(analysisFENs[analysisMoveNumber], gameId, playerColor, pColor, isSpectator, oColor, null);
        }
        moveListBox.appendChild(moveNumberDiv);
        for (const m of moveSplit){
            const moveDiv = document.createElement('div');
            moveDiv.classList.add('move-list-row-element');
            moveDiv.innerText = m;
            moveDiv.id = 'move_id-' + String(totalMoves);
            moveDiv.onclick = function (event){
                resetFences();
                const newAnalysisMoveNumber = parseInt(event.target.id.split('-')[1]) + 1;
                swapSelectedMoveDiv(analysisMoveNumber, newAnalysisMoveNumber);
                analysisMoveNumber = newAnalysisMoveNumber;
                setupBoardFromFEN(analysisFENs[analysisMoveNumber], gameId, playerColor, pColor, isSpectator, oColor, null);
            }
            moveListBox.appendChild(moveDiv);
            totalMoves += 1;
        }
        analysisMoveNumber = totalMoves;
    }

    // Create partial FENs
    analysisFENs = createPartialFENs(moveList, totalMoves, analysisFENs);

    // Set up buttons
    const analysisInit = document.getElementById('analysis-init');
    analysisInit.addEventListener('click',  function (event){
        resetFences();
        if (analysisMoveNumber > 0) {
            const prevMovDiv = document.getElementById('move_id-' + String(analysisMoveNumber - 1));
            prevMovDiv.classList.remove('selected');
        }
        analysisMoveNumber = 0;
        setupBoardFromFEN(analysisFENs[0], gameId, playerColor, pColor, isSpectator, oColor, null);
    });

    const analysisForward = document.getElementById('analysis-forward');
    analysisForward.addEventListener('click',  function (event){
        if (analysisMoveNumber < totalMoves) {
            swapSelectedMoveDiv(analysisMoveNumber, analysisMoveNumber + 1);
            analysisMoveNumber += 1;
            setupBoardFromFEN(analysisFENs[analysisMoveNumber], gameId, playerColor, pColor, isSpectator, oColor, null);
        }
    });

    const analysisBackward = document.getElementById('analysis-backward');
    analysisBackward.addEventListener('click',  function (event){
            swapSelectedMoveDiv(analysisMoveNumber, analysisMoveNumber - 1);
            if (analysisMoveNumber > 0) {
                resetFences();
                analysisMoveNumber -= 1;
                setupBoardFromFEN(analysisFENs[analysisMoveNumber], gameId, playerColor, pColor, isSpectator, oColor, null);
            }
    });

    const analysisEnd = document.getElementById('analysis-end');
    analysisEnd.addEventListener('click',  function (event){
        swapSelectedMoveDiv(analysisMoveNumber, analysisFENs.length - 1);
        analysisMoveNumber = analysisFENs.length - 1;
        setupBoardFromFEN(analysisFENs[analysisMoveNumber], gameId, playerColor, pColor, isSpectator, oColor, null);
    });

    document.addEventListener('keydown',  function (e){
        e = e || window.event;

        if (e.keyCode == '38') {
            // up arrow
            analysisEnd.click();
        }
        else if (e.keyCode == '40') {
            // down arrow
            analysisInit.click();
        }
        else if (e.keyCode == '37') {
           // left arrow
            analysisBackward.click();
        }
        else if (e.keyCode == '39') {
           // right arrow
            analysisForward.click();
        }
    });
}

/*
Game termination options
*/

function abort(gameSocket, playerColor){
    const drawMessage = JSON.stringify({
        'action': 'abort',
        'player_color': playerColor
    });
    gameSocket.send(drawMessage);
    const abort = document.getElementById('abort-button');
    abort.style.display = 'none';
}

function resign(gameSocket, playerColor){
    const resignationMessage = JSON.stringify({
        'action': 'resign',
        'player_color': playerColor
    });
    gameSocket.send(resignationMessage);

    // Hide draw offer box
    const drawOfferBox = document.getElementById('draw-box')
    if (drawOfferBox !== null)
        drawOfferBox.style.display = 'none';
}

function sendDrawOffer(gameSocket, playerColor){
    const drawMessage = JSON.stringify({
        'action': 'draw_offer',
        'player_color': playerColor
    });
    gameSocket.send(drawMessage);
    const draw = document.getElementById('draw-button');
    draw.style.display = 'none';
}

function setupGameTerminationOptions(gameSocket, playerColor) {
    if (playerColor !== null){  // Not spectator
        const abortButton = document.getElementById('abort-button');
        abortButton.onclick = function (event) {
            abort(gameSocket, playerColor);
        };

        const resignButton = document.getElementById('resign-button');
        resignButton.onclick = function (event) {
            resign(gameSocket, playerColor);
        };

        const drawButton = document.getElementById('draw-button');
        drawButton.onclick = function (event) {
            sendDrawOffer(gameSocket, playerColor);
        };
    }
}

function acceptDraw(data, gameSocket) {
    // Accepting other player's offer
    const drawMessage = JSON.stringify({
        'action': 'draw_accept',
        'player_color': playerColor
    });
    gameSocket.send(drawMessage);

    // Hide draw offer box
    const drawBox = document.getElementById('draw-box');
    drawBox.style.display = 'none';
}

function rejectDraw(data, gameSocket) {
    // Rejecting other player's offer
    const drawMessage = JSON.stringify({
        'action': 'draw_reject',
        'player_color': playerColor
    });
    gameSocket.send(drawMessage);

    // Hide draw offer box
    const drawBox = document.getElementById('draw-box');
    drawBox.style.display = 'none';

    // Show draw button again
    const draw = document.getElementById('draw-button');
    draw.style.display = 'inline-block';
}

function rejectedDraw(data) {
    // Other player rejected my draw offer
    // Show draw button again
    const draw = document.getElementById('draw-button');
    draw.style.display = 'inline-block';
}

function drawOffer(data, gameSocket) {
    const draw = document.getElementById('draw-button');
    const _drawOfferItems = document.getElementById('draw-offer-box')
    const drawBox = document.getElementById('draw-box');
    // if (!draw)
    //    acceptDraw(data, gameSocket);

    drawBox.style.display = 'inline-block';
    // Hide draw offer button
    draw.style.display = 'none'; //visibility = 'hidden';
    if (_drawOfferItems === null){ // only if rematch hasn't been proposed
        // Show draw proposal
        const drawText = document.createElement('div');
        drawText.classList.add('rematch-text');
        drawText.textContent = 'Draw? '

        // Create buttons
        const accept = document.createElement('button');
        accept.classList.add('accept');
        accept.innerHTML = '<span class="fa fa-check">';
        accept.addEventListener('click', () => acceptDraw(data, gameSocket));
        const reject = document.createElement('button');
        reject.classList.add('deny');
        reject.innerHTML = '<span class="fa fa-close">';
        reject.addEventListener('click', () => rejectDraw(data, gameSocket));

        // Rematch box items
        const drawOfferItems = document.createElement('div');
        drawOfferItems.classList.add('rematch-response');
        drawOfferItems.id = 'draw-offer-box'
        drawOfferItems.appendChild(reject);
        drawOfferItems.appendChild(accept);

        // Put everything together
        drawBox.appendChild(drawText);
        drawBox.appendChild(drawOfferItems);
    }
}

function afterMoveLogic(data, pColor, isSpectator, oColor, gameSocket, updateTurn=true) {
    // Set turn
    if (updateTurn) {
        let activeColor = setActivePlayer(data, pColor, isSpectator, oColor, gameSocket);
        window.myTurn = (activeColor === pColor);
    }

    // Hide draw offer box
    const drawBox = document.getElementById('draw-box');
    drawBox.style.display = 'none';

    // Set time
    setTime(data['last_color'], data['remaining_time']);
    const moveCount = parseInt(data['move_count']);
    if ((moveCount > 1) && activeUsername !== null) {
        startTimer(data['active_color'], gameSocket);

        // Hide abort button
        const abort = document.getElementById('abort-button');
        abort.style.display = 'none';
        
        if (!isSpectator) {
            // Show game options box
            const gameOptions = document.getElementById('game-options-box');
            gameOptions.style.display = 'inline-block';

            // Show resign button
            const resign = document.getElementById('resign-button');
            resign.style.display = 'inline-block';

            // Show draw button
            const draw = document.getElementById('draw-button');
            draw.style.display = 'inline-block';
        }
    }
}

/*
Rematch
*/

function sendRematchChallenge(gameSocket) {
    const challengedUsername = JSON.parse(document.getElementById('opponent').textContent);
    const opponentIsBot = JSON.parse(document.getElementById('opponent-bot').textContent);
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";

    if (opponentIsBot){
        const matchmakingSocket = new WebSocket(
            ws_scheme
            +'://'
            + window.location.host
            + '/ws/matchmaking/'
            + '0/null/'
        );

        matchmakingSocket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            switch (data['action']) {
                case 'match_details':
                    matchmakingSocket.close();
                    window.location.replace(window.location.protocol + "//" + window.location.host + "/game/" + data['game_id']);
                    break;
                case 'matchmaking_failed':
                    switch (data['reason']){
                        case 'Game already in progress':
                            matchmakingSocket.close();
                            const joinActiveGameButton = document.getElementById("join-active-game");
                            joinActiveGameButton.innerText = data['reason'] + ': ' +
                                data['white_player_username'] + ' (' + data['white_player_rating'] + ') vs ' +
                                data['black_player_username'] + ' (' + data['black_player_rating'] + ')';
                            joinActiveGameButton.classList.remove('hidden');
                            joinActiveGameButton.classList.add('alert');
                            joinActiveGameButton.classList.add('alert-danger');
                            joinActiveGameButton.onclick = function (){
                                window.location.replace(window.location.protocol + "//" + window.location.host + "/game/" + data['game_id']);
                            }
                            break;
                    }
                    break;
            }
        };
    
        matchmakingSocket.onopen = function (e) {
            // TODO: Might need to wait for connection
            const requestMatch = JSON.stringify({
                'action': 'request_bot_match',
                'time': JSON.parse(document.getElementById('total-time-per-player').textContent) / 60,
                'increment': JSON.parse(document.getElementById('increment').textContent),
                'bot_pool': true,
                'bot_username': challengedUsername,
                'bot_color': JSON.parse(document.getElementById('player-color').textContent),
            });
            matchmakingSocket.send(requestMatch);
        };
    
        matchmakingSocket.onclose = function (e) {
            const waitingAnimationContainer = document.getElementById('waitingAnimationContainer');
            if (waitingAnimationContainer)
                waitingAnimationContainer.remove();
        };
    }else{
        const challengeProposal = JSON.stringify({
            'action': 'challenge_rematch',
            'challenger': JSON.parse(document.getElementById('player').textContent),
            'challenged': JSON.parse(document.getElementById('opponent').textContent),
            'game_id': JSON.parse(document.getElementById('game-id').textContent),
            'challenged_color': JSON.parse(document.getElementById('player-color').textContent), // Switches colors
            'time': JSON.parse(document.getElementById('total-time-per-player').textContent) / 60,
            'increment': JSON.parse(document.getElementById('increment').textContent),
            'rated': JSON.parse(document.getElementById('rated').textContent)
        });
        gameSocket.send(challengeProposal);
    }

    // Remove rematch button
    const rematchButton = document.getElementById('rematch-button');
    rematchButton.style.display = 'none'; //visibility = 'hidden';

    // Create waiting animation
    const waitingAnimation = document.createElement('div');
    waitingAnimation.classList.add('lds-ring');
    waitingAnimation.id = 'waitingAnimation';
    waitingAnimation.innerHTML = '<div></div><div></div><div></div><div></div>';
    const rematchBox = document.getElementById('rematch-box');
    rematchBox.appendChild(waitingAnimation);
}

function processChallengeResponse(data, gameSocket) {
    if (data['response'] === 'accept'){
        window.location.replace("http://" + window.location.host + "/game/" + data['game_id']);
    }else{
        const waitingAnimation = document.getElementById('waitingAnimation');
        if (waitingAnimation)
            waitingAnimation.remove();
    }
    //gameSocket.close();
}

// Function to handle accepting a challenge
function acceptChallenge(data, gameSocket) {
    var rated = false;
    // If rated in data, to value
    if (data['rated'] === 'true')
        rated = true;
    else{
        rated = false;
    }
    const challengeResponse = JSON.stringify({
        'action': 'challenge_response',
        'challenger': data['challenger'],
        'challenged': data['challenged'],
        'player_color': data['player_color'],
        'time': data['time'],
        'increment': data['increment'],
        'rated': rated,
        'response': 'accept'
    });
    gameSocket.send(challengeResponse);
}

// Function to handle rejecting a challenge
function rejectChallenge(data, gameSocket) {
    // Implement your logic to reject the challenge with the given ID
    const listItem = document.getElementById('challenge_' + data['challenger']);
    listItem.remove();
    const challengeResponse = JSON.stringify({
        'action': 'challenge_response',
        'player_color': playerColor,
        'challenger': data['challenger'],
        'challenged': data['challenged'],
        'response': 'reject'
    });

    // Remove rematch box
    const rematchBox = document.getElementById('rematch-box');
    rematchBox.style.display = 'none';

    // Communicate rejection
    gameSocket.send(challengeResponse);
}

function processChallengeRequest(data, gameSocket) {

    // Check that game ID and opponent match
    const gameId = JSON.parse(document.getElementById('game-id').textContent);
    const opponent = JSON.parse(document.getElementById('opponent').textContent);
    if (gameId && opponent && data['game_id'] === gameId && data['challenger'] === opponent) {
        // Remove waiting animation
        const waitingAnimation = document.getElementById('waitingAnimation');
        if (waitingAnimation !== null)
            waitingAnimation.remove()

        // Get rematch button. If it doesn't exist, accept rematch directly?
        const rematchButton = document.getElementById('rematch-button');
        const _rematchBoxItems = document.getElementById('challenge_' + data['challenger']);
        if (!rematchButton)
            acceptChallenge(data, challengeSocket);
        else if (_rematchBoxItems === null){ // only if rematch hasn't been proposed
            const rematchBox = document.getElementById('rematch-box');
            rematchBox.classList.add('rematch-box');

            // Hide rematch button
            rematchButton.style.display = 'none'; //visibility = 'hidden';

            // Show rematch proposal
            const rematchText = document.createElement('div');
            rematchText.classList.add('rematch-text');
            rematchText.textContent = 'Rematch? '

            // Create buttons
            const acceptRematchButton = document.createElement('button');
            acceptRematchButton.classList.add('accept');
            acceptRematchButton.innerHTML = '<span class="fa fa-check">';
            acceptRematchButton.addEventListener('click', () => acceptChallenge(data, gameSocket));
            const rejectRematchButton = document.createElement('button');
            rejectRematchButton.classList.add('deny');
            rejectRematchButton.innerHTML = '<span class="fa fa-close">';
            rejectRematchButton.addEventListener('click', () => rejectChallenge(data, gameSocket));

            // Rematch box items
            const rematchBoxItems = document.createElement('div');
            rematchBoxItems.classList.add('rematch-response');
            rematchBoxItems.id = 'challenge_' + data['challenger'];
            rematchBoxItems.appendChild(rejectRematchButton);
            rematchBoxItems.appendChild(acceptRematchButton);

            // Put everything together
            rematchBox.appendChild(rematchText);
            rematchBox.appendChild(rematchBoxItems);
        }
    }
}

/*
Initialise websocket
 */
function createWebsocket(gameId, playerColor, pColor, isSpectator, oColor, analysisFENs, PGN, timeEnd){
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    var gameSocket = new WebSocket(
        ws_scheme
        +'://'
        + window.location.host
        + '/ws/game/'
        + gameId
        + '/'
    )

    gameSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        const board = document.getElementById('board-' + gameId);
        switch (data['action']) {
            case 'FEN':
                FEN = data['FEN'];
                setupBoardFromFEN(data['FEN'], gameId, playerColor, pColor, isSpectator, oColor, gameSocket);
                break;
            case 'PGN':
                if (PGN === undefined) {
                    PGN = data['PGN'];
                    if (parseInt(data['move_count']) > 0)
                        createAnalysisPanel(PGN, gameId, playerColor, pColor, isSpectator, oColor, analysisFENs);
                }
                break;
            case 'place_fence':
                // TODO: Assert integrity of received data, i.e. subwallId matches center coords
                const subwallId = data['wall_type'] + '-' +
                    data['row'] + '-' + data['col'] + '-' + 'true';  // data['subwallId'];
                const subwall = board.querySelector('[subwall-id=' + subwallId + ']');
                const receiveFenceEvent = new Event('receiveFenceEvent');
                subwall.dispatchEvent(receiveFenceEvent);
                setWallNumber(data);

                // Set walls left flag
                if (data['player_color'] === pColor)
                    window.wallsLeft = data['remaining_fences'] > 0;

                afterMoveLogic(data, pColor, isSpectator, oColor, gameSocket);
                break;
            case 'move_pawn':
                // const sourceSquareId = 's' + '-' + data['source_row'] + '-' + data['source_col'];
                const targetSquareId = 's' + '-' + data['target_row'] + '-' + data['target_col'];
                const targetSquare = board.querySelector('[square-id=' + targetSquareId + ']');
                const movePawnEvent = new CustomEvent('movePawnEvent', {'detail': data});
                targetSquare.dispatchEvent(movePawnEvent);

                afterMoveLogic(data, pColor, isSpectator, oColor, gameSocket);
                break;
            case 'pawn_moves':
                // Show current valid pawn moves
                const validSquaresStr = data['valid_squares'];
                const squareList = squareStr2List(validSquaresStr)
                for (const squareCoords of squareList) {
                    const square = document.getElementById('s-' + squareCoords[0] + '-' + squareCoords[1]);
                    const validPawnMove = document.createElement('div');
                    validPawnMove.classList.add('valid-pawn-move');
                    validPawnMove.id = data['player_color'] + '-' + 'move';
                    validPawnMove.square = square;
                    square.appendChild(validPawnMove);
                }
                break;
            case 'game_over':
                setWinner(data, pColor, isSpectator, oColor, gameSocket);
                timeEnd = data['end_time'];

                // Stop timer
                if (activeInterval)
                    clearInterval(activeInterval);

                // Hide abort button
                const abort = document.getElementById('abort-button');
                abort.style.display = 'none';

                // Hide draw box
                const drawOfferBox = document.getElementById('draw-box');
                if (drawOfferBox !== null)
                    drawOfferBox.style.display = 'none';

                // Delete pawn moves
                removeValidPawnMovesEvent(null);
                break;
            case 'draw_offer':
                if (!isSpectator)
                    drawOffer(data, gameSocket);
                break;
            case 'draw_reject':
                if (!isSpectator)
                    rejectedDraw(data);
                break;
            case 'challenge_rematch':  // Receiving a rematch challenge request
                if (!isSpectator)
                    processChallengeRequest(data, gameSocket);
                break;
            case 'challenge_response':  // Receiving the answer to user's rematch challenge
                processChallengeResponse(data, gameSocket);
                break;
        }
    };

    gameSocket.onopen = function (e) {
        requestBoardState(gameSocket, playerColor);
        requestValidPawnMoves(gameSocket, playerColor);
        // Request time check
        requestTimeCheck(gameSocket, playerColor);

        const errorDiv = document.getElementById('reconnecting-error');
        if (errorDiv !== null){
            errorDiv.remove();
        }

        const board = document.getElementById('board-'+gameId);
        if (board !== null){
            // TODO: Consider just updating the board and not recreating it...
            // Reseting board ...
            board.innerHTML = '';
            createBoard(gameId, playerColor, isSpectator, gameSocket);
        }
    }

    gameSocket.onclose = function (e) {
        console.error('Chat socket closed unexpectedly');

        // Disconnected... Attempting to reconnect?
        if (timeEnd === null){ // Game has not ended... reconnect
            // Ref: https://stackoverflow.com/questions/22431751/websocket-how-to-automatically-reconnect-after-it-dies
            const errorDiv = document.getElementById('reconnecting-error');
            if (errorDiv === null) {
                const errorDiv = document.createElement('div');
                const container = document.getElementById('game-sidebar-container');
                errorDiv.classList.add('game-error');
                //errorDiv.classList.add('alert-danger');
                errorDiv.innerHTML = '<b>Disconnected</b> <br> Attempting to reconnect...'
                errorDiv.id = 'reconnecting-error'
                container.appendChild(errorDiv);
            }

            setTimeout(function() {
                gameSocket = createWebsocket(gameId, playerColor, pColor, isSpectator, oColor, analysisFENs, PGN, timeEnd);
            }, 1000);
        }
    };

    return gameSocket
}


/*
Player and game information
 */

var activeUsername = '';
window.myTurn = '';
window.wallsLeft = true;
var FEN = '';
var analysisMoveNumber = 0;
const scriptElement = document.querySelector(`script[src*="load_board.js"]`);
FEN = scriptElement.dataset.fen;
const gameId = scriptElement.dataset.gameid;
const pColor = scriptElement.dataset.pcolor;  // Color of the player (bottom player)
const oColor = scriptElement.dataset.ocolor;  // Color of the opponent (top player)
const playerColor = scriptElement.dataset.playercolor;  // Color of the player. None if player is spectator
const playerUsername = scriptElement.dataset.playerusername; // JSON.parse(document.getElementById('player').textContent);
const opponentUsername = scriptElement.dataset.opponentusername; // JSON.parse(document.getElementById('opponent').textContent);
const timeEnd = scriptElement.dataset.timeend;
const isSpectator = (playerColor !== 'white') & (playerColor !== 'black');
const tutorial = scriptElement.dataset.tutorial !== undefined;
var PGN = scriptElement.dataset.pgn;
if (isSpectator)
    window.myTurn = false;

document.addEventListener("DOMContentLoaded", function() {
    // const scriptElement = document.currentScript;
    /*
    Game analysis
     */
    var analysisFENs = [' / /E1E9/10 10/1'];
    if (FEN !== undefined && tutorial) {
        analysisFENs = [FEN];
    }

    if (PGN !== undefined && PGN !== 'None' && tutorial) {
        createAnalysisPanel(PGN, gameId, playerColor, pColor, isSpectator, oColor, analysisFENs);
        analysisMoveNumber = 0;
    }

    /*
    Create websocket
     */
    var gameSocket = null;
    if (!tutorial)
        gameSocket = createWebsocket(gameId, playerColor, pColor, isSpectator, oColor, analysisFENs, PGN, timeEnd);

    /*
    Setup board
    */
    window.onload = function (){
        createBoard(gameId, playerColor, isSpectator, gameSocket);
        setupBoardFromFEN(FEN, gameId, playerColor, pColor, isSpectator, oColor, gameSocket);
        if (!tutorial)
            setupGameTerminationOptions(gameSocket, playerColor);
    };
});