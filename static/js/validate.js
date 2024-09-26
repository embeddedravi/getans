// import otherFile from 'init.js';


document.getElementById('DropDownList1').classList.toggle('hidden', !dropdownOpen1);
document.documentElement.classList.toggle('dark', isDark);

let dropdown_1 = document.getElementById('DropdownMenuButton1');

dropdown_1.addEventListener('click', () => {
    dropdownOpen1 = !dropdownOpen1;
    localStorage.setItem('dropdownOpen1', dropdownOpen1 ? 'opened' : 'closed');
    document.getElementById('DropDownList1').classList.toggle('hidden', !dropdownOpen1);
})

let signInForm = document.getElementById('signin_form');
if(signInForm) {
    signInForm.addEventListener('submit', (event) => {
        event.preventDefault();
        let email  = signupForm.querySelector('input[name="email"]');
        let password  = signupForm.querySelector('input[name="password"]');
        let terms  = signupForm.querySelector('input[name="terms"]');

        let jsonData = getFormDataJson(signInForm);

        let responseMessage = document.getElementById('response_msg_indicator');
        responseMessage.classList.toggle('hidden', false);
        
        if (!isValidEmail(email) || !isValidPassword(password) || !isValidTerms(terms)) {
            responseMessage.innerText = 'Please fill in the required fields';
            return false;
        }

        responseMessage.innerText = 'Logging in...';
        ajaxPostJsonAsync("/signin", event=>handleResponse(event,responseMessage), jsonData)
        return true;
    });
}

let signupForm = document.getElementById('signup_form');

if(signupForm) {

   let confirm_pass = document.getElementById('confirm_password');
   confirm_pass.addEventListener('input', () => {
      const password = document.getElementById('password').value;
      const confirmPassword = document.getElementById('confirm_password').value;
      const passwordIndicator = document.getElementById('password_indicator');
      const confirmPasswordIndicator = document.getElementById('confirm_password_indicator');
      const isValid = confirmPassword === password;
      confirmPasswordIndicator.classList.toggle('hidden', isValid);
  });

    signupForm.addEventListener('submit', (event) => {
        event.preventDefault();

        let firstName  = signupForm.querySelector('input[name="first_name"]');
        let lastName  = signupForm.querySelector('input[name="last_name"]');
        let email  = signupForm.querySelector('input[name="email"]');
        let password  = signupForm.querySelector('input[name="password"]');
        // let repassword = signupForm.querySelector('input[name="confirm_password"]');
        let terms  = signupForm.querySelector('input[name="terms"]');
        const jsonData = getFormDataJson(signupForm);
        // console.log(jsonData);

        let responseMessage = document.getElementById('response_msg_indicator');
        responseMessage.classList.toggle('hidden', false);
        
        if (!isValidEmail(email) || !validateInput(password.value, /^[a-zA-Z0-9]{6,30}$/, 'password_indicator')  || !isValidTerms(terms) || !validateInput(firstName, /^[a-zA-Z ]{3,30}$/, 'first_name_indicator') || !validateInput(lastName, /^[a-zA-Z ]{3,30}$/, 'last_name_indicator')) {
            responseMessage.innerText = 'Please fill in the required fields';
            return false;
        }

        ajaxPostJsonAsync("/signup", event=>handleResponse(event,responseMessage), jsonData)

        responseMessage.innerText = 'Creating account...';
        return true;
    });
}

const modalClose = () => {
    const modal = document.getElementById('modalElement');
    const contentEle = document.getElementById('contentElement');
    modal.classList.toggle('hidden', true);
    contentEle.classList.toggle('pointer-events-none', false);
    modal.innerHTML = '';
}

const handleResponse = (event, respElm) => {
    const response = JSON.parse(event.responseText);
    respElm.innerText = response.message;
    respElm.classList.toggle('text-green-500', false);
    respElm.classList.toggle('text-red-500', false);
    respElm.classList.toggle('text-orange-500', false);
    respElm.classList.toggle('text-blue-500', false);

    switch (response.status) {
        case Constant.Status.SUCCESS:
            respElm.classList.add('text-green-500');
            break;
        case Constant.Status.ERROR:
            respElm.classList.add('text-red-500');
            break;
        case Constant.Status.INFO:
            respElm.classList.add('text-orange-500');
            break;
        case Constant.Status.WARNING:
            respElm.classList.add('text-blue-500');
            break;
    }

    respElm.classList.toggle('hidden', false);
    if (response.redirect.length>0) {
        respElm.innerText  = respElm.innerText + ' Redirecting to signin page in 2 seconds...';
        setTimeout(() => {
            window.location.href = response.redirect;
        }, 2000);
    }
    if(response.isModal){
        const modal = document.getElementById('modalElement');
        const contentEle = document.getElementById('contentElement');
        modal.innerHTML = response.mdlText;
        modal.classList.toggle('hidden', false);
        contentEle.classList.toggle('pointer-events-none', true);
        // Add event listener to close button
        const closeButton = modal.querySelector('#closeModal');
        const closeButtonTop = modal.querySelector('#closeModalTop');
        if(closeButton) closeButton.addEventListener('click', modalClose);
        if(closeButtonTop) closeButtonTop.addEventListener('click', modalClose);
    }
};

