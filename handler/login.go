package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"getans/model"
	"getans/mongodb"
	"getans/tmpl"
	"net/http"
	"time"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

func SignInHandler(w http.ResponseWriter, r *http.Request) {

	w.Header().Set("Content-Type", "text/html")
	if r.Method == "POST" {
		email := r.FormValue("email")
		password := r.FormValue("password")

		fmt.Fprintf(w, email+password+" updated")
		return
	}
	Breadcrumbs := []tmpl.BreadCrumbs{
		{URL: "#", Name: "Sign In"},
	}

	page := tmpl.Page{
		Title:       "GetAns - Sign In", // Set your page title here
		Links:       "",                 // Set your links here
		JsLinks:     "",                 // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
	}

	page.MakePage(w, r, tmpl.SigninPage)

}

func SignUpHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []tmpl.BreadCrumbs{
		{URL: "#", Name: "Sign Up"},
	}

	page := tmpl.Page{
		Title:       "GetAns - Sign Up", // Set your page title here
		Links:       "",                 // Set your links here
		JsLinks:     "",                 // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
	}

	if r.Method == http.MethodPost {
		var userData model.UserDetails
		err := json.NewDecoder(r.Body).Decode(&userData)
		if err != nil {
			resp := model.ErrorResponse()
			resp.Message = err.Error()
			resp.MakeResponse(w)
			return
		}
		dobTime, err := time.Parse("2006-01-02", userData.Dob)
		if err != nil {
			resp := model.ErrorResponse()
			resp.Message = err.Error()
			resp.MakeResponse(w)
			return
		}

		// Calculate the age
		age := time.Since(dobTime).Hours() / 24 / 365

		// Check if the age is within the valid range
		if age < 18 || age > 120 {
			resp := model.ErrorResponse()
			resp.Message = "Age must be between 18 and 120"
			resp.MakeResponse(w)
			return
		}
		hash, err := model.HashPassword(userData.Password)
		if err != nil {
			resp := model.ErrorResponse()
			resp.Message = err.Error()
			resp.MakeResponse(w)
			return
		}
		userData.Password = hash

		if !model.VerifyPassword("password", hash) {
			resp := model.ErrorResponse()
			resp.Message = "Password is not password"
			resp.MakeResponse(w)
			return
		}
		mongodb.Connect()
		coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
		defer mongodb.Disconnect()

		result, err := coll.InsertOne(context.TODO(), userData)

		if err != nil {
			resp := model.ErrorResponse()
			resp.Message = err.Error()
			resp.MakeResponse(w)
		} else {
			resp := model.SuccessResponse()
			// Get the inserted ID as a string
			_, ok := result.InsertedID.(primitive.ObjectID)
			if !ok {
				resp := model.ErrorResponse()
				resp.Message = "InsertedID is not of type ObjectID"
				resp.MakeResponse(w)
				return
			}

			// insertedIDStr := objID.Hex()
			resp.Status = model.Status.Success
			resp.Message = "User created successfully. "
			resp.Redirect = "/signin"
			resp.MakeResponse(w)
		}
		return
	} else {
		page.MakePage(w, r, tmpl.SignupPage)
	}
}

func LogoutHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, you've been logged out")
}
