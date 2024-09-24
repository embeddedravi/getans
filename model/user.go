package model

import (
	"encoding/base64"

	"golang.org/x/crypto/bcrypt"
)

type UserDetails struct {
	FirstName string `json:"first_name" bson:"first_name" validate:"required"`
	LastName  string `json:"last_name" bson:"last_name" validate:"required"`
	Mobile    string `json:"mobile" bson:"mobile" validate:"required"`
	Email     string `json:"email" bson:"email" validate:"required,email"`
	Password  string `json:"password" bson:"password" validate:"required"`
	Gender    string `json:"gender" bson:"gender" validate:"required"`
	Dob       string `json:"dob" bson:"dob" validate:"required"`
}

func HashPassword(password string) (string, error) {

	// Hash the password with the salt
	hashedPassword, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}
	// fmt.Fprint(os.Stdout, "password: "+password+"\n"+"saltc: "+base64.StdEncoding.EncodeToString(salt)+"\n")
	// Return the salt and hashed password as separate strings
	return base64.StdEncoding.EncodeToString(hashedPassword), nil
}

func VerifyPassword(password string, hashedPassword string) bool {
	// Decode the salt value
	hashedPasswordBytes, err := base64.StdEncoding.DecodeString(hashedPassword)
	if err != nil {
		return false
	}

	// Directly compare the password with the stored hashed password
	err = bcrypt.CompareHashAndPassword([]byte(hashedPasswordBytes), []byte(password))
	return err == nil

}
