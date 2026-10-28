package com.quiz.rag.model;

public class GameHistoryItem {
    private final String roomCode;
    private final String mode;
    private final int score;
    private final int totalQuestions;
    private final int correctAnswers;
    private final String opponentUsername;
    private final Integer opponentScore;
    private final String result;
    private final String playedAt;
    private final String sourceDocument;
    /** Raw server JSON for this entry, kept so a detail screen can read questionLog without a second request. */
    private final String rawJson;

    public GameHistoryItem(String roomCode, String mode, int score, int totalQuestions, int correctAnswers,
                            String opponentUsername, Integer opponentScore, String result, String playedAt,
                            String sourceDocument, String rawJson) {
        this.roomCode = roomCode;
        this.mode = mode;
        this.score = score;
        this.totalQuestions = totalQuestions;
        this.correctAnswers = correctAnswers;
        this.opponentUsername = opponentUsername;
        this.opponentScore = opponentScore;
        this.result = result;
        this.playedAt = playedAt;
        this.sourceDocument = sourceDocument;
        this.rawJson = rawJson;
    }

    public String getRoomCode() { return roomCode; }
    public String getMode() { return mode; }
    public int getScore() { return score; }
    public int getTotalQuestions() { return totalQuestions; }
    public int getCorrectAnswers() { return correctAnswers; }
    public String getOpponentUsername() { return opponentUsername; }
    public Integer getOpponentScore() { return opponentScore; }
    public String getResult() { return result; }
    public String getPlayedAt() { return playedAt; }
    public String getSourceDocument() { return sourceDocument; }
    public String getRawJson() { return rawJson; }
}
