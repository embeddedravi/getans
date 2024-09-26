package main

import (
	"getans/handler"
	"getans/handler/user"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {

	staticDir := "./static"
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticDir))))

	r := mux.NewRouter()
	u := r.PathPrefix("/user").Subrouter()

	r.HandleFunc("/", handler.HomeHandler)
	r.HandleFunc("/signin", handler.SignInHandler)
	r.HandleFunc("/signup", handler.SignUpHandler)
	r.HandleFunc("/logout", handler.LogoutHandler)

	u.HandleFunc("/", user.Profile)

	http.Handle("/", r)
	http.ListenAndServe(":8080", nil)
}
