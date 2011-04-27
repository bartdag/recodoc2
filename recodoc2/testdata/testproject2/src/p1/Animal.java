package p1;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

public interface Animal {
	
	public final static int MAX_AGE = 110;
	
	public final static String DEFAULT_NAME = "CHARLIE";
	
	String getName();
	
	void run();
	
	int getAge();
	
	List<Animal> getChildren();
	
	Collection<Animal> getParents();
	
	void setChildren(List<Animal> children) throws AnimalException, IOException;
	
	void setChildren(List<Animal> children, List<String> names);
	
	String toString();
	
}
