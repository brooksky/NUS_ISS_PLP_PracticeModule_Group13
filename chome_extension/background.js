console.log('');
console.log('background start');


async function getChartData(videoId, videoDuration) {
    console.log(`getChartData: videoId=${videoId}, videoDuration==${videoDuration}`);
    
    let labelData, goodData, mehData, badData;
    await fetch(`http://localhost:5000/api/chart?videoDuration=${videoDuration}&videoId=${videoId}`)
        .then(response => response.json())
        .then(jsonObject => {
            labelData = jsonObject.label;
            goodData = jsonObject.good;
            mehData = jsonObject.meh;
            badData = jsonObject.bad;
        });

    return {
        label: labelData,
        good: goodData,
        meh: mehData,
        bad: badData
    };
}


async function getCommentData(videoId, text, videoDuration) {
    console.log('getCommentData: videoId='+ videoId + ', duration=' + videoDuration + ', text=' + text);

    let sentimentValue, jumpToSeconds;
    await fetch(`http://localhost:5000/api/comment?videoId=${videoId}&videoDuration=${videoDuration}&commentText=${encodeURIComponent(text)}`)
        .then(response => response.json())
        .then(jsonObject => {
            sentimentValue = jsonObject.sentiment;
            jumpToSeconds = jsonObject.jumpToSec;
        });

    return {
        jumpToSec: jumpToSeconds,
        sentiment: sentimentValue
    };
}

async function initVideo(videoId, videoDuration) {
    console.log('initVideo: videoId='+ videoId);

    await fetch(`http://localhost:5000/api/video?videoId=${videoId}&videoDuration=${videoDuration}`)
        .then(response => response.json())
        .then(jsonObject => console.log('initVideo(): ' + JSON.stringify(jsonObject)));

    return true;
}

const asyncFunctionWithAwait = async (request, sender, sendResponse) => {
    // Bug fix for port closed when using Fetch() + sendResponse()
    // https://stackoverflow.com/questions/54017163/how-to-avoid-the-message-port-closed-before-a-response-was-received-error-when

    if (request.message === 'popup!') {
        console.log(`Received from popup [${request.message}]`);

        chrome.tabs.query({ active:true, windowType:"normal", currentWindow: true }, tabs => { 
            tabs.forEach(tab => {
                chrome.tabs.get(tab.id, current_tab_info => {
                    console.log(`Current tab: id=${tab.id}, url=${current_tab_info.url}`);
                    if (/^https:\/\/www\.youtube\.com\/watch\?v=/.test(current_tab_info.url)) {        
                        chrome.scripting.executeScript(
                            { target: {tabId: tab.id}, files: ['./chart.min.js', './foreground.js']}, 
                            () => console.log('Injected foreground.js') 
                        );
                    }
                }); 
            });
        });
        sendResponse({message:'from background.js to popup.js'});
    }
    
    else if (request.message === 'Video') {
        console.log(`Received Video request. \nvideoId: ${request.videoId}, \nvideoDuration: ${request.videoDuration}`);
        await initVideo(request.videoId, request.videoDuration)
        sendResponse({message:'init video done'});
    }

    else if (request.message === 'Sentiment Chart') {
        console.log(`Received Sentiment Stacked Line Chart request. \nvideoId: ${request.videoId}, \nvideoDuration: ${request.videoDuration}`);
        let chartData = await getChartData(request.videoId, request.videoDuration);
        sendResponse(chartData);
    } 

    else if (request.message === 'Comment') {
        console.log(`Received Comment (${request.commentIndex}) request. \nvideoId: ${request.videoId}, \ncommentText: ${request.commentText}, \nvideoDuration: ${request.videoDuration}`);
        let data = await getCommentData(request.videoId, request.commentText, request.videoDuration);
        sendResponse(data);
    }
}


// Listen to message from foreground.js and reply
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    asyncFunctionWithAwait(request, sender, sendResponse);
    return true;
});
