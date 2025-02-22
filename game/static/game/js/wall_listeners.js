const MAX_ROW = 9;
const MAX_COL = 9;

export function wallClickCallback(wall, nextCenter, nextWall){
    wall.hasFence = true;
    nextCenter.hasFence = true;
    nextWall.hasFence = true;
}

export function wallUnclickCallback(wall, nextCenter, nextWall){
    wall.hasFence = false;
    nextCenter.hasFence = false;
    nextWall.hasFence = false;
}

export function changeFenceColorCallback(checkTurn, color){
    return function (wall, nextCenter, nextWall){
        if (!checkTurn || window.myTurn & window.wallsLeft){
            wall.style.backgroundColor = color;
            nextCenter.style.backgroundColor = color;
            nextWall.style.backgroundColor = color;
        }
    }
}

export function changeFencePropertyCallback(className){
    return function (wall, nextCenter, nextWall){
        wall.classList.add(className);
        nextCenter.classList.add(className);
        nextWall.classList.add(className);
    }
}

export function changeCursorType(checkTurn, type){
    return function (wall, nextCenter, nextWall){
        if (!checkTurn || window.myTurn & window.wallsLeft){
            wall.style.cursor = type;
            // nextCenter.style.backgroundColor = color;
            // nextWall.style.backgroundColor = color;
        }
    }
}

export function placeWallSoundCallback(){
    return function (wall, nextCenter, nextWall){
        const sound = new Audio(window.sound_dir + '/place_wall_2.wav');
        sound.play();
    }
}

export function sendFenceMessageCallback(gameSocket, playerColor){
    return function (wall, nextCenter, nextWall) {
        if (!window.myTurn)
            return

        const next = (nextWall.row > wall.row) || (nextWall.col > wall.col);

        // Placing a fence
        const subwallId = wall.wallType + '-' + wall.row + '-' + wall.col + '-' + next;
        const message = JSON.stringify({
            'action': 'place_fence',
            'player_color': playerColor,
            'wall_type': wall.wallType,
            'row': Math.min(wall.row, nextWall.row),
            'col': Math.min(wall.col, nextWall.col),
            'subwallId': subwallId
        });
        gameSocket.send(message);
    }
}

export function wallEvent(next, callbacks, alternativeNext = true) {
    return function (event) {
        const board = event.currentTarget.board;

        // Get coordinates of next wall
        const row = event.currentTarget.row;
        const col = event.currentTarget.col;
        const wallType = event.currentTarget.wallType;

        // Get wall
        const wallId = wallType + '-' + row + '-' + col;
        const wall = board.querySelector('[wall-id=' + wallId + ']');
        if (wall.hasFence) {  // Do nothing
            // TODO: Consider switching next if that is possible
            return
        }

        // Proceed with logic
        let nextCenterCol = col;
        let nextCenterRow = row;
        let nextRow = row;
        let nextCol = col;
        if (wallType === 'h') {
            if (nextCol === 0) {
                nextCol = col + 1;
            } else if (nextCol === MAX_COL - 1) {
                nextCol = col - 1;
                nextCenterCol = col - 1;
            } else if (next) {
                nextCol = col + 1;
            } else {
                nextCol = col - 1;
                nextCenterCol = col - 1;
            }
        } else {  // wall type is 'v'
            if (nextRow === 0) {
                nextRow = row + 1;
            } else if (nextRow === MAX_ROW - 1) {
                nextRow = row - 1;
                nextCenterRow = row - 1;
            } else if (next) {
                nextRow = row + 1;
            } else {  // Putting wall above
                nextRow = row - 1;
                nextCenterRow = row - 1;
            }
        }

        // Change color of next wall
        const cond = nextCol >= 0 && nextCol < MAX_COL && nextRow >= 0 && nextRow < MAX_ROW;
        if (cond) {
            // Change color of next center
            const centerId = 'c-' + nextCenterRow + '-' + nextCenterCol;
            const nextCenter = board.querySelector('[wall-id=' + centerId + ']');

            // Change color of next wall
            const nextWallId = wallType + '-' + nextRow + '-' + nextCol;
            const nextWall = board.querySelector('[wall-id=' + nextWallId + ']');

            if (!nextWall.hasFence && !nextCenter.hasFence) {
                // Execute transactions in callbacks
                for (let k in callbacks) {
                    callbacks[k](wall, nextCenter, nextWall);
                }
            } else if (alternativeNext){ // Try opposite next wall in case actual next wall is occupied
                wallEvent(!next, callbacks, false)(event);
            }
        }
    }
}