package main

import (
	"fmt"
	"getans/tmpl"
	"html/template"
	"net/http"

	"github.com/gorilla/mux"
)

var SigninPage, SignupPage, IndexPage *template.Template

func HomeHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")

	Breadcrumbs := []tmpl.BreadCrumbs{}

	page := tmpl.Page{
		Title:       "GetAns - Home Page", // Set your page title here
		Links:       "",                   // Set your links here
		JsLinks:     "",                   // Set your JavaScript links here
		Breadcrumbs: Breadcrumbs,
	}

	page.MakePage(w, r, IndexPage)

}

func SignInHandler(w http.ResponseWriter, r *http.Request) {

	w.Header().Set("Content-Type", "text/html")
	if r.Method == "POST" {
		email := r.FormValue("email")
		password := r.FormValue("password")
		fmt.Fprintf(w, "EMAIL: %s<br>", email)
		fmt.Fprintf(w, "PASSWORD: %s<br>", password)
		fmt.Fprintf(w, "METHID: %s<br>", r.Method)
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

	page.MakePage(w, r, SigninPage)

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

	page.MakePage(w, r, SignupPage)
}

func init() {
	Path := "D:/Project/Go/getans/tmpl/layout/"

	SigninPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content/signin.html"))
	SignupPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content/signup.html"))
	IndexPage = template.Must(template.New("base.html").ParseFiles(Path+"base.html", Path+"common.html", Path+"content.html"))

}

func main() {

	staticDir := "./static"
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticDir))))

	r := mux.NewRouter()
	r.HandleFunc("/", HomeHandler)
	r.HandleFunc("/signin", SignInHandler)
	r.HandleFunc("/signup", SignUpHandler)

	http.Handle("/", r)
	http.ListenAndServe(":8080", nil)
}
