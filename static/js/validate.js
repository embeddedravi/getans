
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
        let email  = signInForm.elements[0];
        let password  = signInForm.elements[1];
        let terms  = signInForm.elements[2];

        let responseMessage = document.getElementById('response_msg_indicator');
        responseMessage.classList.toggle('hidden', false);
        
        if (!isValidEmail(email) || !isValidPassword(password) || !isValidTerms(terms)) {
            responseMessage.innerText = 'Please fill in the required fields';
            return false;
        }
        responseMessage.innerText = 'Logging in...';
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

        let firstName  = signupForm.elements[0];
        let lastName  = signupForm.elements[1];
        let dob  = signupForm.elements[2];
        let moblie  = signupForm.elements[3];

        let email  = signupForm.elements[4];
        let password  = signupForm.elements[5];
      //   let repassword = signupForm.elements[6];
        let terms  = signupForm.elements[7];

        const formData = new FormData(signupForm);
        const jsonData = Object.fromEntries(formData.entries());
        console.log(jsonData);

        let responseMessage = document.getElementById('response_msg_indicator');
        responseMessage.classList.toggle('hidden', false);
        
        if (!isValidEmail(email) || !validateInput(password.value, /^[a-zA-Z0-9]{6,30}$/, 'password_indicator') || !validateInput(firstName, /^[a-zA-Z ]{3,30}$/, 'first_name_indicator') || !isValidTerms(terms) || !validateInput(firstName, /^[a-zA-Z ]{3,30}$/, 'first_name_indicator') || !validateInput(lastName, /^[a-zA-Z ]{3,30}$/, 'last_name_indicator')) {
            responseMessage.innerText = 'Please fill in the required fields';
            return false;
        }

        ajaxPostJsonAsync("/signup", event=>handleResponse(event,responseMessage), jsonData)

        responseMessage.innerText = 'Creating account...';
        return true;
    });
}

const handleResponse = (event, responseMessageElement) => {
    const response = JSON.parse(event.responseText);
    responseMessageElement.innerText = response.message;
    if (response.success) {
        responseMessageElement.classList.add('text-green-500');
        responseMessageElement.classList.remove('text-red-500');
        if (response.redirect) {
            responseMessageElement.innerText  = responseMessageElement.innerText + ' Redirecting to signin page in 2 seconds...';
            setTimeout(() => {
                window.location.href = response.redirect;
            }, 2000);
        }
    } else {
        responseMessageElement.classList.add('text-red-500');
        responseMessageElement.classList.remove('text-green-500');
    }
};

