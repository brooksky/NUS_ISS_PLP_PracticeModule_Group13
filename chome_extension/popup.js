// When the button is clicked, inject setPageBackgroundColor into current page
document.getElementById("activate").addEventListener("click", async () => {
    // let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    console.log('Popup button is clicked');
    chrome.runtime.sendMessage({message: 'popup!'}, response => {
        console.log(`background script replied=${response.message}`);
    });
});
