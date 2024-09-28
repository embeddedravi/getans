package defines

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

var DbURI, LayoutPath, DocRootPath, CookieName, ClientHashKey string

func init() {
	err := godotenv.Load()
	if err != nil {
		fmt.Println("Error loading .env file")
		panic(err)
	}
	DbURI = os.Getenv("MONGODB_URI")
	LayoutPath = os.Getenv("LAYOUT_PATH")
	DocRootPath = os.Getenv("DOCUMENT_ROOT")
	CookieName = os.Getenv("COOKIE_NAME")
	ClientHashKey = os.Getenv("CLIENT_HASH_KEY")
	// If CookieName is empty, set it to "ClientID"
	if CookieName == "" {
		CookieName = "ClientID"
	}
	if ClientHashKey == "" {
		ClientHashKey = "24@#dffgrretgfgdd"
	}

}
