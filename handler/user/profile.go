package user

import (
	"main/model"
	"net/http"
)

func Profile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []model.BreadCrumbs{
		{URL: "#", Name: "Profile"},
	}

	page := model.Page{
		Title:       "GetAns - User Profile", // Set your page title here
		Links:       "",                      // Set your links here
		JsLinks:     "",                      // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
	}

	page.MakePage(w, r, model.IndexPage)

}
