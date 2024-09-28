package handler

import (
	"context"
	"encoding/json"
	"main/defines"
	"main/model"
	"main/mongodb"
	"net/http"
	"time"

	"github.com/mitchellh/mapstructure"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

func SignInHandler(w http.ResponseWriter, r *http.Request) {

	clientDetails := model.GetClientDetails(r)
	// fmt.Print(clientDetails)
	if clientDetails.IsLoggedIn {
		if model.VerifyLogin(clientDetails) {
			http.Redirect(w, r, "/", http.StatusFound)
			return
		}
	}

	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []model.BreadCrumbs{
		{URL: "#", Name: "Sign In"},
	}

	page := model.Page{
		Title:       "GetAns - Sign In", // Set your page title here
		Links:       "",                 // Set your links here
		JsLinks:     "",                 // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
		Client:      clientDetails,
	}

	if r.Method == http.MethodPost {
		var userData model.MdlUserSigninForm

		// Parse the request body
		if err := json.NewDecoder(r.Body).Decode(&userData); err != nil {
			model.ErrorResponse(err.Error()).
				MakeResponse(w)
			return
		}

		// Validate terms and conditions
		if !userData.Terms {
			model.ErrorResponse("Must agree with terms and conditions").
				MakeResponse(w)
		}

		// Check if the email is already registered
		mongodb.Connect()
		coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
		defer mongodb.Disconnect()

		result := coll.FindOne(context.TODO(), bson.M{"email": userData.Email})

		if result.Err() == nil {
			var userDetails model.MdlUserDetails
			err := result.Decode(&userDetails)
			if err != nil {
				model.ErrorResponse(err.Error()).
					MakeResponse(w)
				return
			}

			if model.VerifyPassword(userData.Password, userDetails.Password) {

				// Create session
				clientDetails := model.MdlClientDetails{
					ClientIP:    r.RemoteAddr,
					UserAgent:   r.UserAgent(),
					IsLoggedIn:  true,
					IsBlocked:   false,
					BlockedAt:   "",
					UserDetails: userDetails,
				}
				res, err := clientDetails.JsonString()
				if err != nil {
					model.ErrorResponse(err.Error()).
						MakeResponse(w)
					return
				}

				base64, err := model.Encrypt([]byte(defines.ClientHashKey), []byte(res))
				if err != nil {
					model.ErrorResponse(err.Error()).
						MakeResponse(w)
					return
				}

				model.SetCookie(w, defines.CookieName, base64)

				model.SuccessResponse("User logged in successfully. Redirecting to home page...").
					SetStatus(defines.StatusSuccess).
					SetRedirect("/").
					MakeResponse(w)

			} else {
				model.ErrorResponse("Incorrect email or password").
					MakeResponse(w)
			}
		} else {
			model.ErrorResponse("Incorrect email or password").
				MakeResponse(w)
		}

	} else {
		page.MakePage(w, r, model.SigninPage)
	}

}

func SignUpHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "json")

	clientDetails := model.GetClientDetails(r)

	Breadcrumbs := []model.BreadCrumbs{
		{URL: "#", Name: "Sign Up"},
	}

	page := model.Page{
		Title:       "GetAns - Sign Up", // Set your page title here
		Links:       "",                 // Set your links here
		JsLinks:     "",                 // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
		Client:      clientDetails,
	}

	if r.Method == http.MethodPost {

		var userData model.MdlUserSignupForm
		// Parse the request body
		if err := json.NewDecoder(r.Body).Decode(&userData); err != nil {
			model.ErrorResponse(err.Error()).
				MakeResponse(w)
			return
		}

		// Validate terms and conditions
		if !userData.Terms {
			model.ErrorResponse("Must agree with terms and conditions").
				MakeResponse(w)
		}
		// Validate the user dob
		dobTime, err := time.Parse("2006-01-02", userData.Dob)
		if err != nil {
			model.ErrorResponse(err.Error()).
				MakeResponse(w)
			return
		}
		// Calculate the age
		age := time.Since(dobTime).Hours() / 24 / 365
		// Check if the age is within the valid range
		if age < 18 || age > 120 {
			model.ErrorResponse("Age must be between 18 and 120").
				MakeResponse(w)
			return
		}
		// Check password length
		if len(userData.Password) < 6 {
			model.ErrorResponse("Password must be at least 8 characters long").
				MakeResponse(w)
			return
		}
		// Check if email is already registered
		if model.IsEmailRegistered(userData.Email) {
			model.ErrorResponse("Email already registered").
				MakeResponse(w)
			return
		}
		// Hash the password
		hash, err := model.HashPassword(userData.Password)
		if err != nil {
			model.ErrorResponse(err.Error()).
				MakeResponse(w)
			return
		}
		userData.Password = hash
		// Insert the user data into the database

		var userDetail model.MdlUserDetails
		if err := mapstructure.Decode(userData, &userDetail); err != nil {
			// handle error
		}
		userDetail.CreatedAt = time.Now().Format("2006-01-02 15:04:05")
		userDetail.UpdatedAt = time.Now().Format("2006-01-02 15:04:05")
		userDetail.Type = "user"
		userDetail.Status = "active"
		userDetail.Verified = false

		mongodb.Connect()
		coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
		defer mongodb.Disconnect()

		result, err := coll.InsertOne(context.TODO(), userDetail)

		if err != nil {
			model.ErrorResponse(err.Error()).
				MakeResponse(w)
		} else {
			// Get the inserted ID as a string
			if _, ok := result.InsertedID.(primitive.ObjectID); !ok {
				model.ErrorResponse("InsertedID is not of type ObjectID").
					MakeResponse(w)
				return
			}

			model.SuccessResponse("User created successfully. Redirecting to sign in page...").
				SetStatus(defines.StatusSuccess).
				SetRedirect("/signin").
				MakeResponse(w)
			// resp := model.SuccessResponse()
			// resp.IsModal = true
			// mdl := model.MdlModel{
			// 	MdlTitle:      "User Created",
			// 	MdlContent:    "User created successfully. " + fmt.Sprint(result.InsertedID),
			// 	UpdateBtnName: "Ok",
			// 	NeedCloseBtn:  true,
			// }
			// resp.MdlText, err = tmpl.RenderTemplate(tmpl.MdlTemplate, mdl)
			// if err != nil {
			// 	model.ErrorResponse(err.Error()).
			// 		MakeResponse(w)
			// 	return
			// }
			// resp.MakeResponse(w)
		}
		return
	} else {
		page.MakePage(w, r, model.SignupPage)
	}
}

func LogoutHandler(w http.ResponseWriter, r *http.Request) {
	model.SetLogout(w)
	http.Redirect(w, r, "/", http.StatusFound)
}
