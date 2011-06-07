package p1;

public @interface AnimalTag {

	int id();
	String fooBar() default "[foo!]";
	String fuzBar();
	boolean theAnimalB();
	byte theAnimalb();
	float theAnimalf();
	
}
