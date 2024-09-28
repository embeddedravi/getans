let dropdownOpen1 = false;
let isDark = false;

const Constant = {
  Status: {
    SUCCESS: 'success',
    ERROR: 'error',
    INFO: 'info',
    WARNING: 'warning'
  }
};

localStorage.getItem('dropdownOpen1') === 'opened' ? dropdownOpen1 = true : dropdownOpen1 = false;
localStorage.getItem('themeName') === 'Dark' ? isDark = true : isDark = false;

/**
 * Validates if the input element's value matches the given regex pattern.
 * @param {HTMLElement} inputElement The HTML element of the input to validate.
 * @param {RegExp} regexPattern The regex pattern to test against.
 * @param {string} errorIndicatorElementId The element id of the error indicator element.
 * @returns {boolean} Whether the input element's value is valid according to the regex pattern.
 */
const validateInput = (inputElement, regexPattern, errorIndicatorElementId) => {
    const errorIndicatorElement = document.getElementById(errorIndicatorElementId);
    if(!errorIndicatorElement){
        console.error(`Error indicator element with id ${errorIndicatorElementId} not found`);
        return false;
    }

    const isValid = regexPattern.test(inputElement.value);
    errorIndicatorElement.classList.toggle('hidden', isValid);
    return isValid;
};


/**
 * Returns true if the input element's value is a valid email address, false otherwise.
 * @param {HTMLElement} element The HTML element of the input.
 * @returns {boolean} Whether the input element's value is a valid email address or not.
 */
const isValidEmail = (element) => {
    const emailRegex = /^[^@]+@[^@]+\.[^@]+$/;
    return validateInput(element, emailRegex, 'email_indicator');
};
/**
 * Returns true if the terms checkbox is checked, false otherwise.
 * @param {HTMLElement} element The HTML element of the terms checkbox.
 * @returns {boolean} Whether the terms checkbox is checked or not.
 */
const isValidTerms = (element) => {
    const termsIndicator = document.getElementById('terms_indicator');

    termsIndicator.classList.toggle('hidden', element.checked);
    return element.checked;
};

/**
 * Returns true if the password is not empty, false otherwise.
 * @param {HTMLElement} element The HTML element of the password input.
 * @returns {boolean} Whether the password is valid or not.
 */
const isValidPassword = (element) => {
    const passwordIndicator = document.getElementById('password_indicator');

    const isValid = element.value !== '';
    passwordIndicator.classList.toggle('hidden', isValid);
    return isValid;
};

/**
 * Given a form, this function returns the form data as a json object.
 * @param {HTMLFormElement} form The form whose data needs to be converted to json.
 * @returns {Object} The form data as a json object.
 */
const getFormDataJson = (form) => {
    const jsonData = {};
    for (const element of form.elements) {
        if (element.name.trim().length !=0) {
            if (element.type === 'radio') {
                if (element.checked) {
                    jsonData[element.name] = element.value;
                }
            }
            else if (element.type === 'checkbox') {
                jsonData[element.name] = element.checked;
            }
            else {
                jsonData[element.name] = element.value;
            }
        }
    }
    return jsonData;
}

/**
 * Toggle the theme between light and dark
 * This function changes the value of the global `isDark` variable and sets the
 * corresponding value in local storage. It also toggles the 'dark' class on the
 * root element of the document, which is used to apply the different styles for
 * the light and dark themes.
 */
const toggleTheme = () => {
    isDark = !isDark;
    localStorage.setItem('themeName', isDark ? 'Dark' : 'Light');
    document.documentElement.classList.toggle('dark', isDark);
}

const logoutClient = () => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/logout');
    xhr.onload = () => {
        if (xhr.status === 200) {
            window.location.reload();
        }
    };
    xhr.send();
}

/**
 * Perform an asynchronous POST request with JSON data
 * @param {string} url The url to make the request to
 * @param {function} callback The callback function to call when the request is complete
 * @param {object} data The JSON serializable data to send in the request body
 */
function ajaxPostJsonAsync(url, callback, data) {
    const jsonData = JSON.stringify(data);
    const xhr = new XMLHttpRequest();
    url += '?rnd=' + getRndNumber(11111, 99999);
    xhr.addEventListener("readystatechange", function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            callback(xhr);
        }
    });
    xhr.open("POST", url, true);
    xhr.setRequestHeader("Content-type", "application/json; charset=utf-8");
    xhr.send(jsonData);
}

/**
 * Perform an asynchronous POST request with JSON data
 * @param {string} url The url to make the request to
 * @param {function} callback The callback function to call when the request is complete
 * @param {object} data The JSON serializable data to send in the request body
 */
function ajaxPostAsync(url, callback, data) {
    const formData = new FormData();
    const jsonData = JSON.stringify(data);
    formData.append("data", jsonData);

    const xhr = new XMLHttpRequest();
    xhr.addEventListener("readystatechange", function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            callback(xhr);
        }
    });
    xhr.open("POST", url, true);
    xhr.overrideMimeType("text/plain; charset=x-user-defined-binary");
    xhr.setRequestHeader("Content-disposition", "form-data");
    xhr.setRequestHeader("X-Requested-With", "xmlhttprequest");
    xhr.send(formData);
}


/**
 * Returns a random number between min (inclusive) and max (inclusive)
 * @param {number} min The minimum value
 * @param {number} max The maximum value
 * @returns {number} The random number
 */
function getRndNumber(min, max) {
    return Math.floor(Math.random() * (max - min)) + min;
}