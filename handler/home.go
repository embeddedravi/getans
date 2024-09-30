package handler

import (
	"main/model"
	"net/http"
)

func HomeHandler(w http.ResponseWriter, r *http.Request) {

	clientDetails := model.GetClientDetails(r)

	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []model.BreadCrumbs{}

	page := model.Page{
		Title:       "GetAns - Home Page", // Set your page title here
		Links:       "",                   // Set your links here
		JsLinks:     "",                   // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
		Client:      clientDetails,
	}

	page.MakePage(w, r, model.IndexPage)
}
