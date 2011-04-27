package p1;

public enum AnimalType {
	
	CARNIVORUS,
	VEGETARIAN,
	NOT_SURE;
	
}

enum SubAnimalType {
	
	SOFT ("soft"),
	HARD ("hard");
	
	private String other;
	
	SubAnimalType(String other) {
		this.other = other;
	}
	
	public String getOther() {
		return other;
	}
	
}
