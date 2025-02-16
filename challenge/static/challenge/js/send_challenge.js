function sendChallenge(prefixId){
    const challengerUsername = JSON.parse(document.getElementById('username').textContent);
    const challengedUsername = document.getElementById(prefixId + '-challenged_username').value;
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const challengeSocket = new WebSocket(
        ws_scheme
        + '://'
        + window.location.host
        + '/ws/challenge/'
        + challengedUsername
        + '/'
    )

    challengeSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        switch (data['action']){
            case 'challenge_response':
                challengeSocket.close();
                if (data['response'] === 'accept'){
                    // Challenge has been accepted, receive game details and join game
                    // document.getElementById("game_id").value = data['game_id'];
                    // document.getElementById("joinChallengeGameForm").submit();
                    window.location.replace(window.location.protocol + '//' + window.location.host + "/game/" + data['game_id']);
                }else {
                    console.log('Challenge rejected');
                    const waitingAnimation = document.getElementById(prefixId+'-waitingAnimation');
                    waitingAnimation.remove();
                    const challengeButton = document.getElementById(prefixId+'-challenge-button');
                    challengeButton.style.display = 'inline-block'; //visibility = 'hidden';
                }
                break;
        }
    };

    challengeSocket.onopen = function (e){
        // TODO: Might need to wait for connection

        if (challengedUsername !== challengerUsername) {
            const time = document.getElementById(prefixId+"-time").value
            const increment = document.getElementById(prefixId+"-increment").value
            const challengeProposal = JSON.stringify({
                'action': 'challenge_proposal',
                'challenger_color': 'random', // document.querySelector('input[name="player_color"]:checked').value,
                'time': time,
                'increment': increment
            });
            console.log('Challenge proposal', challengeProposal);
            challengeSocket.send(challengeProposal);

            // Remove challenge button
            const challengeButton = document.getElementById(prefixId + '-challenge-button');
            challengeButton.style.display = 'none'; //visibility = 'hidden';

            // Create waiting animation
            const waitingAnimation = document.createElement('div');
            waitingAnimation.classList.add('lds-ring');
            waitingAnimation.id = prefixId + '-waitingAnimation';
            waitingAnimation.innerHTML = '<div></div><div></div><div></div><div></div>';
            const challengeBox = document.getElementById(prefixId + '-challenge-box');
            challengeBox.appendChild(waitingAnimation);
        }
    };

    challengeSocket.onclose = function(e) {
        const waitingAnimation = document.getElementById('waitingAnimation');
        if (waitingAnimation)
            waitingAnimation.remove();
        // console.error('Chat socket closed unexpectedly');
    };

}

function sendRematchChallenge(){
    const challengedUsername = JSON.parse(document.getElementById('opponent').textContent);
    const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const challengeSocket = new WebSocket(
        ws_scheme
        + '://'
        + window.location.host
        + '/ws/challenge/'
        + challengedUsername
        + '/'
    )

    challengeSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log('Message received', data)
        switch (data['action']){
            case 'challenge_response':
                challengeSocket.close();
                if (data['response'] === 'accept'){
                    // Challenge has been accepted, receive game details and join game
                    // document.getElementById("game_id").value = data['game_id'];
                    // document.getElementById("joinChallengeGameForm").submit();
                    window.location.replace("http://" + window.location.host + "/game/" + data['game_id']);
                }else{
                    const waitingAnimation = document.getElementById('waitingAnimation');
                    if (waitingAnimation)
                        waitingAnimation.remove();
                }
                break;
        }
    };

    challengeSocket.onopen = function (e){
        // TODO: Might need to wait for connection
        const challengeProposal = JSON.stringify({
            'action': 'challenge_rematch',
            // 'challenger_color': document.querySelector('input[name="player_color"]:checked').value
            'game_id': JSON.parse(document.getElementById('game-id').textContent),
            'challenged_color': JSON.parse(document.getElementById('player-color').textContent), // Switches colors
            'time': JSON.parse(document.getElementById('total-time-per-player').textContent) / 60,
            'increment': JSON.parse(document.getElementById('increment').textContent)
        });
        console.log('Challenge proposal', challengeProposal);
        console.log('Color', JSON.parse(document.getElementById('player-color').textContent));
        challengeSocket.send(challengeProposal);
    };

    challengeSocket.onclose = function(e) {
        const waitingAnimation = document.getElementById('waitingAnimation');
        if (waitingAnimation)
            waitingAnimation.remove();
        console.error('Chat socket closed unexpectedly');
    };

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