export function squareStr2List(squaresStr){
    const squareStrList = squaresStr.match(/.{1,2}/g)
    const squareList = [];

    for (const squareStr of squareStrList){
        const col = squareStr.charCodeAt(0) - 65;
        const row = parseInt(squareStr[1]) - 1;
        squareList.push([row, col])
    }

    return squareList
}