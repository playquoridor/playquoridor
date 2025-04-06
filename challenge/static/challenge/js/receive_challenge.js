// Function to handle receiving a challenge
function receiveChallenge(username){
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const challengeSocket = new WebSocket(
        ws_scheme
        + '://'
        + window.location.host
        + '/ws/challenge/'
        + username
        + '/'
    )

    challengeSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        switch (data['action']){
            case 'challenge_rematch':
                console.log('Challenge received', data);

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
                        acceptRematchButton.addEventListener('click', () => acceptChallenge(data, challengeSocket));
                        const rejectRematchButton = document.createElement('button');
                        rejectRematchButton.classList.add('deny');
                        rejectRematchButton.innerHTML = '<span class="fa fa-close">';
                        rejectRematchButton.addEventListener('click', () => rejectChallenge(data, challengeSocket));

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
                // Not break: Challenge is also displayed in notifications?
                break;
            case 'challenge_proposal':
                console.log('Challenge received', data)
                const challengeList = document.getElementById('challenges-list');
                const listItem = document.createElement('a');
                // listItem.classList.add('challenge');
                listItem.classList.add('dropdown-item');
                listItem.id = 'challenge_' + data['challenger'];
                listItem.value = data['challenger'];
                /* listItem.textContent = data['challenger'] + ' '; */

                const playerNameChallenge = document.createElement('span');
                playerNameChallenge.classList.add('challenge-player');
                playerNameChallenge.innerHTML = '<b>' + data['challenger'] + '</b>' + ' (' + data['time'] + '+' + data['increment'] + ') ' +  '<br> Your color: ' + data['player_color'] + '<br>';


                /* Challenge response */
                const acceptButton = document.createElement('button');
                acceptButton.classList.add('accept');
                acceptButton.innerHTML = '<span class="fa fa-check">';
                acceptButton.addEventListener('click', () => acceptChallenge(data, challengeSocket));
                const rejectButton = document.createElement('button');
                rejectButton.classList.add('deny');
                rejectButton.innerHTML = '<span class="fa fa-close">';
                rejectButton.addEventListener('click', () => rejectChallenge(data, challengeSocket));

                const challengeResponse = document.createElement('span');
                challengeResponse.classList.add('challenge-response');
                challengeResponse.appendChild(rejectButton);
                challengeResponse.appendChild(acceptButton);

                /* Put items together */
                listItem.appendChild(playerNameChallenge);
                listItem.appendChild(challengeResponse);
                challengeList.appendChild(listItem);

                // Update badge
                const badge = document.getElementById('challenges-badge');
                if (badge.textContent === '0')
                    badge.classList.toggle('hidden')
                badge.textContent = String(parseInt(badge.textContent) + 1);
                break;
            case 'challenge_response':
                challengeSocket.close();
                if (data['response'] === 'accept') {
                    // Challenge has been accepted, receive game details and join game
                    // console.log('Joining challenge game')
                    // document.getElementById("game_id").value = data['game_id'];
                    // document.getElementById("joinChallengeGameForm").submit();
                    window.location.replace("http://" + window.location.host + "/game/" + data['game_id']);
                }
                else{
                    console.log('Rejected. Shouldn\'t get here', data)
                }
                break;
        }
    };

    challengeSocket.onopen = function (e){
    };

    challengeSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };
}

// Function to handle accepting a challenge
function acceptChallenge(data, challengeSocket) {
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
        'player_color': data['player_color'],
        'time': data['time'],
        'increment': data['increment'],
        'rated': rated,
        'response': 'accept'
    });
    challengeSocket.send(challengeResponse);
}

// Function to handle rejecting a challenge
function rejectChallenge(data, challengeSocket) {
    // Implement your logic to reject the challenge with the given ID
    const listItem = document.getElementById('challenge_' + data['challenger']);
    listItem.remove();
    const challengeResponse = JSON.stringify({
        'action': 'challenge_response',
        'challenger': data['challenger'],
        'response': 'reject'
    });

    // Decrease counter
    const badge = document.getElementById('challenges-badge');
    badge.textContent = String(parseInt(badge.textContent) - 1);
    if (badge.textContent === '0')
        badge.classList.add('hidden')

    const challengeList = document.getElementById('challenges-list');
    if (badge.textContent === '0')
        challengeList.classList.toggle('hidden')

    // Communicate rejection
    challengeSocket.send(challengeResponse);
}

// Ensure the challenges list is hidden initially
//challengesListContainer.classList.add('hidden');

// Receive challenge
const username = JSON.parse(document.getElementById('username').textContent)
receiveChallenge(username);