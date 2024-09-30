package user

import (
	"main/model"
	"net/http"
)

func Profile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")

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

	page.MakePage(w, r, model.ProfilePage)
}
