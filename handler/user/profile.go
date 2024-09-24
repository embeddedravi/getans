package handler

import (
	"getans/tmpl"
	"net/http"
)

func Profile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []tmpl.BreadCrumbs{
		{URL: "#", Name: "Profile"},
	}

	page := tmpl.Page{
		Title:       "GetAns - User Profile", // Set your page title here
		Links:       "",                      // Set your links here
		JsLinks:     "",                      // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
	}

	page.MakePage(w, r, tmpl.IndexPage)

}
