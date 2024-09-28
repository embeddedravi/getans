package model

import (
	"context"
	"encoding/json"
	"fmt"
	"main/defines"
	"main/mongodb"
	"net/http"
	"strings"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

type MdlUserSignupForm struct {
	FirstName string `json:"first_name" bson:"first_name" validate:"required min=3 max=30"`
	LastName  string `json:"last_name" bson:"last_name" validate:"required min=3 max=30"`
	Mobile    string `json:"mobile" bson:"mobile" validate:"required"`
	Email     string `json:"email" bson:"email" validate:"required,email"`
	Password  string `json:"password" bson:"password" validate:"required"`
	Gender    string `json:"gender" bson:"gender" validate:"required oneof=male female other"`
	Dob       string `json:"dob" bson:"dob" validate:"required"`
	Terms     bool   `json:"terms"  validate:"required"`
}

type MdlUserDetails struct {
	FirstName string             `json:"firstname" bson:"firstname" validate:"required min=3 max=30"`
	LastName  string             `json:"lastname" bson:"lastname" validate:"required min=3 max=30"`
	Mobile    string             `json:"mobile" bson:"mobile" validate:"required"`
	Email     string             `json:"email" bson:"email" validate:"required,email"`
	Password  string             `json:"password" bson:"password" validate:"required"`
	Gender    string             `json:"gender" bson:"gender" validate:"required oneof=male female other"`
	Dob       string             `json:"dob" bson:"dob" validate:"required"`
	Verified  bool               `json:"verified" bson:"verified"`
	Status    string             `json:"status" bson:"status"`
	Type      string             `json:"type" bson:"type"`
	CreatedAt string             `json:"created_at" bson:"created_at"`
	UpdatedAt string             `json:"updated_at" bson:"updated_at"`
	UserID    primitive.ObjectID `json:"_id" bson:"_id"`
}

type MdlUserSigninForm struct {
	Email    string `json:"email" bson:"email" validate:"required"`
	Password string `json:"password" bson:"password" validate:"required"`
	Terms    bool   `json:"terms" bson:"terms" validate:"required"`
}
type MdlClientDetails struct {
	ClientIP    string         `json:"client_ip" bson:"client_ip"`
	UserAgent   string         `json:"user_agent" bson:"user_agent"`
	IsLoggedIn  bool           `json:"is_logged_in" bson:"is_logged_in"`
	IsBlocked   bool           `json:"is_blocked" bson:"is_blocked"`
	BlockedAt   string         `json:"blocked_at" bson:"blocked_at"`
	UserDetails MdlUserDetails `json:"user_details" bson:"user_details"`
}

func GetClientDetails(r *http.Request) MdlClientDetails {

	var clientDetails MdlClientDetails

	cookie := GetCookies(r)

	for _, c := range cookie {
		if c.Name == defines.CookieName {
			clientDetails.Initialize(c.Value)
			return clientDetails
		}
	}
	clientDetails.IsLoggedIn = false
	return clientDetails

}

func (m *MdlClientDetails) Initialize(hash string) bool {
	jsonString, err := Decrypt(defines.ClientHashKey, hash)
	// fmt.Println(jsonString)
	if err != nil {
		return false
	}
	decoder := json.NewDecoder(strings.NewReader(string(jsonString)))
	err = decoder.Decode(&m)
	if err != nil {
		fmt.Println(err)
		return false
	}
	return true
}
func (m MdlClientDetails) JsonString() (string, error) {
	var buf strings.Builder
	encoder := json.NewEncoder(&buf)
	err := encoder.Encode(m)
	if err != nil {
		return "", err
	}
	return buf.String(), nil
}

func VerifyLogin(clientDetails MdlClientDetails) bool {
	mongodb.Connect()
	coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
	defer mongodb.Disconnect()

	result := coll.FindOne(context.TODO(), bson.M{"_id": clientDetails.UserDetails.UserID})

	var userDetails MdlUserDetails
	err := result.Decode(&userDetails)
	// fmt.Println(userDetails)
	if err != nil {
		fmt.Println(err)
		return false
	}

	if userDetails.Password != clientDetails.UserDetails.Password || userDetails.UpdatedAt != clientDetails.UserDetails.UpdatedAt {
		return false
	}

	return true
}
