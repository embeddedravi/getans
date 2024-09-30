package main

import (
	"fmt"
	"log"
	"main/defines"
	"main/handler"
	"main/handler/user"
	"main/model"
	"net/http"

	"github.com/gorilla/mux"
)

func main() {
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(defines.DocRootPath))))

	r := mux.NewRouter()
	u := r.PathPrefix("/user").Subrouter()

	r.HandleFunc("/", handler.HomeHandler)
	r.HandleFunc("/signin", handler.SignInHandler)
	r.HandleFunc("/signup", handler.SignUpHandler)
	r.HandleFunc("/logout", handler.LogoutHandler)

	u.HandleFunc("/", user.Profile)

	http.Handle("/", r)

	if !model.IsPortAvailable(8080) {
		log.Println("Port 8080 is not available")
		fmt.Println("Press a key to continue...")
		fmt.Scanln()
	} else {
		log.Println("Listening on :8080")
		log.Fatal(http.ListenAndServe(":8080", nil))
	}
}
