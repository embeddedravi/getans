package model

import (
	"bytes"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"html/template"
	"io"
	"main/defines"
	"main/mongodb"
	"net"
	"net/http"

	"go.mongodb.org/mongo-driver/bson"
	"golang.org/x/crypto/bcrypt"
)

func IsPortAvailable(port int) bool {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return false
	}
	ln.Close()
	ln.Close()
	return true
}

func RenderTemplate(tmpl *template.Template, data MdlModel) (string, error) {
	var buf bytes.Buffer
	err := tmpl.Execute(&buf, data)
	if err != nil {
		return "", err
	}
	return buf.String(), nil
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

func IsEmailRegistered(email string) bool {

	// Check if the email is already registered
	mongodb.Connect()
	coll := mongodb.Client.Database("GetansDb").Collection("userDetails")
	defer mongodb.Disconnect()

	count, err := coll.CountDocuments(context.TODO(), bson.M{"email": email})
	return err == nil && count > 0
}

func pad(plaintext []byte, blockSize int) []byte {
	padding := blockSize - len(plaintext)%blockSize
	padtext := bytes.Repeat([]byte{byte(padding)}, padding)
	return append(plaintext, padtext...)
}

func unpad(plaintext []byte, blockSize int) ([]byte, error) {
	length := len(plaintext)
	unpadding := int(plaintext[length-1])

	if unpadding > blockSize {
		return nil, fmt.Errorf("invalid padding")
	}

	return plaintext[:length-unpadding], nil
}

func Encrypt(skey, plaintext []byte) (string, error) {

	pword := []byte(skey)
	hash := sha256.Sum256(pword)
	key := hash[:]

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", err
	}

	// Pad the plaintext to a multiple of the block size
	plaintext = pad(plaintext, aes.BlockSize)

	ciphertext := make([]byte, aes.BlockSize+len(plaintext))
	iv := ciphertext[:aes.BlockSize]
	if _, err := io.ReadFull(rand.Reader, iv); err != nil {
		return "", err
	}

	stream := cipher.NewCTR(block, iv)
	stream.XORKeyStream(ciphertext[aes.BlockSize:], plaintext)

	// Return the ciphertext as a base64-encoded string
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func Decrypt(skey, text string) (string, error) {

	pword := []byte(skey)
	hash := sha256.Sum256(pword)
	key := hash[:]

	block, err := aes.NewCipher([]byte(key))
	if err != nil {
		return "", err
	}

	// Decode the base64-encoded ciphertext
	ciphertext, err := base64.StdEncoding.DecodeString(text)
	if err != nil {
		return "", err
	}

	iv := ciphertext[:aes.BlockSize]
	ciphertext = ciphertext[aes.BlockSize:]

	stream := cipher.NewCTR(block, iv)
	stream.XORKeyStream(ciphertext, ciphertext)

	// Remove the padding from the plaintext
	plaintext, err := unpad(ciphertext, aes.BlockSize)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}

func SetCookie(w http.ResponseWriter, cookieName string, value string, maxAge ...int) {
	var mAge int
	mAge = 3600
	if len(maxAge) > 0 {
		mAge = int(maxAge[0])
	}

	cookie := &http.Cookie{
		Name:     cookieName,
		Value:    value,
		MaxAge:   mAge, // 1 hour
		Secure:   true,
		HttpOnly: true,
	}
	http.SetCookie(w, cookie)
}

func GetCookies(r *http.Request) []*http.Cookie {
	return r.Cookies()

}

func SetLogout(w http.ResponseWriter) {
	SetCookie(w, defines.CookieName, "", -1)
}
