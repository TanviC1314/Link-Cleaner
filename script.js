/**************************************************
 * STEP 1: DOM ELEMENTS (NOT core topic → PROVIDED)
 **************************************************/

const urlInput = document.getElementById("urlInput");

const cleanUtmBtn = document.getElementById("cleanUtmBtn");
const removeAllParamsBtn = document.getElementById("removeAllParamsBtn");
const resetBtn = document.getElementById("resetBtn");
const copyBtn = document.getElementById("copyBtn");

const keepHashToggle = document.getElementById("keepHashToggle");
const lowercaseHostToggle = document.getElementById("lowercaseHostToggle");

const outputText = document.getElementById("outputText");
const previewText = document.getElementById("previewText");
const statusPill = document.getElementById("statusPill");



/**************************************************
 * STEP 2: STATE (NOT core topic → PROVIDED)
 **************************************************/

let cleanedUrl = "";
let status = "Ready";



/**************************************************
 * STEP 3: RENDER FUNCTION (MOSTLY PROVIDED)
 **************************************************/

function render() {
  statusPill.textContent = status;

  outputText.textContent = cleanedUrl || "—";

  if (cleanedUrl) {
    previewText.textContent = formatPreview(cleanedUrl);
  } else {
    previewText.textContent = "—";
  }
}



/**************************************************
 * STEP 4: PURE FUNCTIONS (🔥 CORE TOPIC 🔥)
 * This is where YOU practice functions
 **************************************************/

// Validate URL string
function isValidUrl(text) {
 
  if (text=="") return false
  try{
    new URL(text);
    return true
  }
  catch(_){
    return false
  }
}


// Safely convert string to URL object
function toUrlObject(text) {
  // 👉 WRITE YOUR CODE HERE
  // Instructions:
  // 1. Try new URL(text)
  // 2. If success → return URL object
  // 3. If error → return null
  //https://example.com/page?x=1#top
  let url;
  try{
    url =new URL(text);
    const obj={
      host: url.hostname,
      path:url.pathname,
      search:url.search,
      hash:url.hash
    }
    return obj
  }catch(_){
    return null
  }
  //else

    
  //   try{
  //   return new URL(text);
  // }catch(_){
  //   return null
  // }

  console.log(url.hostname)
}


// Remove ONLY tracking parameters (UTM, gclid, etc.)
function cleanUtm(urlObj, options) {
  // 👉 WRITE YOUR CODE HERE
  /*
    Instructions:
    1. Create an array of tracking keys:
       utm_source, utm_medium, utm_campaign,
       utm_term, utm_content,
       gclid, fbclid, mc_cid, mc_eid

    2. Loop through the array
    3. For each key → remove it from urlObj.searchParams

    4. If options.keepHash === false
       → remove hash (#...)

    5. If options.lowercaseHost === true
       → lowercase ONLY the domain (host)

    6. Return final cleaned URL as string
  */
}


// Remove ALL query parameters
function removeAllParams(urlObj, options) {
  // 👉 WRITE YOUR CODE HERE
  /*
    Instructions:
    1. Remove entire query string
    2. Apply keepHash option
    3. Apply lowercaseHost option
    4. Return cleaned URL string
  */
}


// Format preview (small UI helper → PARTIALLY RELATED)
function formatPreview(urlString) {
  // 👉 WRITE YOUR CODE HERE
  /*
    Instructions:
    1. Create URL object from urlString
    2. Return: hostname + pathname
       Example: example.com/page
  */
}



/**************************************************
 * STEP 5: EVENT HANDLERS (LOGIC FLOW PROVIDED)
 **************************************************/

cleanUtmBtn.addEventListener("click", function () {
  const input = urlInput.value.trim();

  if (!isValidUrl(input)) {
    status = "Invalid link";
    render();
    return;
  }

  const urlObj = toUrlObject(input);
  if (!urlObj) {
    status = "Invalid link";
    render();
    return;
  }

  const options = {
    keepHash: keepHashToggle.checked,
    lowercaseHost: lowercaseHostToggle.checked
  };

  // 👉 WRITE YOUR CODE HERE
  // Call cleanUtm() and store result in cleanedUrl

  status = "UTM removed";
  render();
});


removeAllParamsBtn.addEventListener("click", function () {
  const input = urlInput.value.trim();

  if (!isValidUrl(input)) {
    status = "Invalid link";
    render();
    return;
  }

  const urlObj = toUrlObject(input);

  const options = {
    keepHash: keepHashToggle.checked,
    lowercaseHost: lowercaseHostToggle.checked
  };

  // 👉 WRITE YOUR CODE HERE
  // Call removeAllParams() and store result in cleanedUrl

  status = "All params removed";
  render();
});


resetBtn.addEventListener("click", function () {
  urlInput.value = "";
  cleanedUrl = "";
  status = "Ready";
  render();
});


copyBtn.addEventListener("click", function () {
  if (!cleanedUrl) {
    status = "Nothing to copy";
    render();
    return;
  }

  navigator.clipboard.writeText(cleanedUrl);
  status = "Copied ✅";
  render();
});



/**************************************************
 * STEP 6: INITIAL RENDER (PROVIDED)
 **************************************************/

render();
