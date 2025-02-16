
function joinMatchmaking(event, time, increment){
    event.preventDefault();
    //console.log(sessionStorage.getItem('matchmakingClicked'));
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const matchmakingSocket = new WebSocket(
        ws_scheme
        +'://'
        + window.location.host
        + '/ws/matchmaking/'
        + '0/null/'
    )

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
            'action': 'request_match',
            'time': time,
            'increment': increment
        });
        console.log('Request match', requestMatch);
        matchmakingSocket.send(requestMatch);
    };

    matchmakingSocket.onclose = function (e) {
        /*
        const waitingAnimation = document.getElementById('waitingAnimation');
        if (waitingAnimation)
            waitingAnimation.remove();
        */
        const waitingAnimationContainer = document.getElementById('waitingAnimationContainer');
        if (waitingAnimationContainer)
            waitingAnimationContainer.remove();
        // console.error('Chat socket closed unexpectedly');
    };

    // Remove matchmaking button
    // const matchmakingButton = document.getElementById('matchmaking-button');
    // matchmakingButton.style.display = 'none'; //visibility = 'hidden';

    // Create waiting animation
    const waitingAnimation = document.createElement('div');
    waitingAnimation.classList.add('lds-ring');
    waitingAnimation.id = 'waitingAnimation';
    waitingAnimation.innerHTML = '<div></div><div></div><div></div><div></div>';

    /* Center waiting animation */
    const waitingDiv = document.createElement('div');
    waitingDiv.classList.add('waiting-box');
    waitingDiv.appendChild(waitingAnimation);

    /* Translucent background */
    const waitingAnimationContainer = document.createElement('div');
    waitingAnimationContainer.classList.add('waiting-animation-container');
    waitingAnimationContainer.id = 'waitingAnimationContainer';
    waitingAnimationContainer.appendChild(waitingDiv);

    const matchmakingGrid = document.getElementById('matchmaking-container');
    matchmakingGrid.appendChild(waitingAnimationContainer);
    // matchmakingGrid.appendChild(waitingDiv);

}
