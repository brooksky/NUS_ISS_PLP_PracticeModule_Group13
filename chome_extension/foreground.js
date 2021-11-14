console.log('');
console.log('foreground start');

function getVideoDurationInSeconds() {
    // HH:MM:SS or MM:SS
    duration_str = document.getElementsByClassName('ytp-time-duration')[0].textContent;
    hr_min_min_str = duration_str.split(":"); // [HH, MM, SS] or [MM, SS]

    var duration_seconds;
    if (hr_min_min_str.length === 3) {
        duration_seconds = parseInt(hr_min_min_str[0])*60*60 + parseInt(hr_min_min_str[1])*60 + parseInt(hr_min_min_str[2]);
    } else if (hr_min_min_str.length === 2) {
        duration_seconds = parseInt(hr_min_min_str[0])*60 + parseInt(hr_min_min_str[1]);
    } else {
        console.error("error getVideoDurationInSeconds: " + duration_str);
    }
    return duration_seconds;
}

function getRndInteger(min, max) {
    return Math.floor(Math.random() * (max - min) ) + min;
}

function getRndDouble(min, max) {
    return Math.random() * (max - min)  + min;
}

function getRndIntegerList(list_length, max) {
    return Array.from({length: list_length}, () => Math.floor(Math.random() * max))
}

function getHoursUnitFromSeconds(seconds) {
    var secondsInHour = 60*60;
    return parseInt(seconds / secondsInHour);
}

function getMinutesUnitFromSeconds(seconds) {
    var seconds_in_hour = 60*60;
    var remaining_seconds_left = seconds % seconds_in_hour;
    return parseInt(remaining_seconds_left / 60);
}

function getSecondsUnitFromSeconds(seconds) {
    return seconds % 60;
}

function getTimeStrFromSeconds(seconds) {
    if (seconds >= 60*60) {
        // Time in HH:MM:SS format
        return getHoursUnitFromSeconds(seconds) + ':' + 
            String(getMinutesUnitFromSeconds(seconds)).padStart(2,'0') + ':' + 
            String(getSecondsUnitFromSeconds(seconds)).padStart(2,'0');
    } else {
        // Time in MM:SS format
        return getMinutesUnitFromSeconds(seconds) + ':' + 
            String(getSecondsUnitFromSeconds(seconds)).padStart(2,'0');
    }
}

function getSpanTag(text) {
    var my_tag = document.createElement("span");
    my_tag.className = 'peanut';
    my_tag.style.fontSize = "1.4rem";
    my_tag.style.marginRight = "4px";
    my_tag.appendChild(document.createTextNode(text));

    return my_tag
}

function getVideoId() {
    // Get video ID from URL of current tab
    var videoId = null;
    window.location.href.split('?')[1].split('&').forEach(query_string => {
        if (query_string.includes("v=")) {
            videoId = query_string.slice(2,);
        }
    });
    
    return videoId;
}

function getHrefTag(random_video_seconds) {
    var videoId = getVideoId();
    var href_display_text = getTimeStrFromSeconds(random_video_seconds);

    var my_tag = document.createElement("a");
    my_tag.setAttribute("href", `https://www.youtube.com/watch?v=${videoId}&t=${random_video_seconds}s`);
    my_tag.appendChild(document.createTextNode(href_display_text));
    
    my_tag.className = 'peanut';

    my_tag.style.color = "#3ea6ff";
    my_tag.style.textDecoration = "none";
    my_tag.style.fontSize = "1.4rem";

    return my_tag
}

function getSentimentEmoticon(random_sentiment) {
    if (random_sentiment < -0.25) {
        return "🔴";
    } else if (random_sentiment > 0.25) {
        return "🟢";
    } else {
        return "🟡";
    }
}


function getSentimentSpanTag(sentiment_value) {
    var text_content = "Sentiment: " + getSentimentEmoticon(sentiment_value) + " (" + Math.round(sentiment_value * 100) / 100 + ")";
    var my_tag = document.createElement("span");
    my_tag.appendChild(document.createTextNode(text_content));
    my_tag.className = 'peanut';

    my_tag.style.marginLeft = "25px";
    my_tag.style.marginRight = "25px";
    my_tag.style.textDecoration = "none";
    my_tag.style.fontSize = "1.4rem";

    return my_tag;
}

function getSentimentStackedLineChart() {
    var canvas = document.createElement('canvas');
    canvas.id = 'sentimentLineChart';
    // canvas.width = '400';
    canvas.height = '30';

    canvas.style.marginLeft = '12px';
    canvas.style.marginRight = '12px';

    return canvas
}

function createSentimentStackedLineChart(label_data, good_data, meh_data, bad_data) {
    const ctx = document.getElementById('sentimentLineChart').getContext('2d');

    const data = {
      labels: label_data,
      datasets: [
        {
          label: 'bad',
          data: bad_data,
          borderColor: 'rgba(255, 0, 0, 0.0)',
          backgroundColor: 'rgba(255, 0, 0, 0.7)',  
          fill: true
        },
        {
          label: 'Meh',
          data: meh_data,
          borderColor: 'rgba(255, 255, 0, 0.0)',
          backgroundColor: 'rgba(255, 255, 0, 0.7)',
          fill: true
        },
        {
          label: 'good',
          data: good_data,
          borderColor: 'rgba(0, 255, 0, 0.0)',
          backgroundColor: 'rgba(0, 255, 0, 0.7)',
          fill: true
        }
      ]
    };

    new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
          responsive: true,
          elements: {
              point: { radius: 0 }
          },
          plugins: {
              title: { display: false },
              legend: { display: false }, 
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          },
          scales: {
            x: { display: false },
            y: {
                display: false,
                stacked: true
            }
          }
        }
      });
}


function getSentimentStackedBarChart() {
    var canvas = document.createElement('canvas');
    canvas.id = 'sentimentChart';
    // canvas.width = '400';
    canvas.height = '30';

    canvas.style.marginLeft = '12px';
    canvas.style.marginRight = '12px';

    return canvas
}


function createSentimentStackedBarChart(label_data, good_data, meh_data, bad_data) {
    var ctx = document.getElementById('sentimentChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: label_data,
            datasets: [
                {
                    label: 'Negative',
                    data: bad_data,
                    backgroundColor: 'red'
                },
                {
                    label: 'Meh',
                    data: meh_data,
                    backgroundColor: 'yellow'
                },
                {
                    label: 'Postive',
                    data: good_data,
                    backgroundColor: 'green'
                }
        
            ]
        },
        options: {
            plugins: {
                title: { display: false },
                legend: { display: false }, 
            },
            interaction: {
                mode: 'index'
            },
            scales: {
                y: {
                    beginAtZero: true,
                    stacked: true,
                    display: false
                },
                x: {
                    stacked: true,
                    display: false
                }
            }
        }
    });
}


function getTextFromCommentTag(commentTag) {
    // ID="comment" -> ID="content-text" -> list of Span tags
    const contextTextTag = Array.from(commentTag.querySelectorAll("#content-text"))[0];
    return contextTextTag ? contextTextTag.textContent : '';
}


function refreshSentimentStackedBarChart(label_data, good_data, meh_data, bad_data) {
    console.log('Received data for Sentiment Stacked Bar Chart.');

    // Remove existing chart if exist.
    var sentimentChart = document.getElementById('sentimentChart');
    if(sentimentChart) { sentimentChart.remove() }

    // Create canvas element for new Stacked Bar Chart
    var player_node = document.getElementById('player-theater-container');
    player_node.parentNode.insertBefore(getSentimentStackedBarChart(), player_node.nextElementSibling);

    // Create the chart with the canvas
    createSentimentStackedBarChart(label_data, good_data, meh_data, bad_data);
}


function refreshSentimentStackedLineChart(label_data, good_data, meh_data, bad_data) {
    console.log('Received data for Sentiment Stacked Line Chart.');

    // Remove existing chart if exist.
    sentimentChart = document.getElementById('sentimentLineChart');
    if(sentimentChart) { sentimentChart.remove() }

    // Create canvas element for new Stacked Line Chart
    var player_node = document.getElementById('player-theater-container');
    player_node.parentNode.insertBefore(getSentimentStackedLineChart(), player_node.nextElementSibling);

    // Create the chart with the canvas
    createSentimentStackedLineChart(label_data, good_data, meh_data, bad_data);
}


///////////////////////////////////////////////////////////////////////////////////////////////////
// MAIN 
///////////////////////////////////////////////////////////////////////////////////////////////////

chrome.runtime.sendMessage({message: 'Video', videoId: getVideoId(), videoDuration: getVideoDurationInSeconds()}, response => {
    console.log('Received data for Video. response: ' + JSON.stringify(response));

    // Create Sentiment Stacked Bar Chart below Video Player
    chrome.runtime.sendMessage({message: 'Sentiment Chart', videoId: getVideoId(), videoDuration: getVideoDurationInSeconds()}, response => {
        // refreshSentimentStackedBarChart(response.label, response.good, response.meh, response.bad);
        refreshSentimentStackedLineChart(response.label, response.good, response.meh, response.bad);
    });

    // Add Video Time Link and Sentiment Score to each comment
    document.querySelectorAll("#comment").forEach((element, index) => {
        var toolbar_tag = element.querySelectorAll('#toolbar');
        if (toolbar_tag.length === 1) {
            chrome.runtime.sendMessage({message: 'Comment', videoId: getVideoId(), commentIndex: index, commentText: getTextFromCommentTag(element), videoDuration: getVideoDurationInSeconds()}
            , response => {
                console.log('Received data for Comment. response.sentiment: ' + JSON.stringify(response));

                // Remove existing text in comments
                Array.from(element.getElementsByClassName('peanut'))
                    .forEach(my_element => my_element.parentNode.removeChild(my_element));

                toolbar_tag[0].appendChild( getSentimentSpanTag(response.sentiment) );
                if (response.jumpToSec) {
                    toolbar_tag[0].appendChild( getSpanTag('Jump to') );
                    toolbar_tag[0].appendChild( getHrefTag(response.jumpToSec) );
                }
            });   
        }
    });

});
