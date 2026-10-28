package com.quiz.rag.model;

public class User {
    private String username;
    private String email;
    private String address;
    private String gender;
    private int age;
    private int avatarId;

    public User(String username, String email, String address, String gender, int age, int avatarId) {
        this.username = username;
        this.email = email;
        this.address = address;
        this.gender = gender;
        this.age = age;
        this.avatarId = avatarId;
    }

    public String getUsername() { return username; }
    public String getEmail() { return email; }
    public String getAddress() { return address; }
    public String getGender() { return gender; }
    public int getAge() { return age; }
    public int getAvatarId() { return avatarId; }
}