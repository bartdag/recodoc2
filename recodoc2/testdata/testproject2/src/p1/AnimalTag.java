package p1;

public @interface AnimalTag {

	int id();
	String fooBar() default "[foo!]";
	boolean theAnimalB();
	byte theAnimalb();
	float theAnimalf();
	
}
